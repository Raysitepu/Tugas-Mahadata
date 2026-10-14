"""Replikasi parsial Ali et al. (2024), Spark SQL dan MLlib pada data LCL.

Prediksi rolling satu langkah (30 menit); evaluasi berdasarkan urutan waktu.
Tidak mengklaim replikasi penuh, efek kausal tarif, atau hasil cloud.
"""
import argparse
import hashlib
import json
import logging
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, PolynomialExpansion
from pyspark.ml.regression import LinearRegression, DecisionTreeRegressor
import pyspark

SEED = 42
FEATURES = ['slot_sin', 'slot_cos', 'dow_sin', 'dow_cos', 'year_sin',
            'year_cos', 'weekend', 'lag1', 'lag48', 'lag336']


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    e = predicted - actual
    mse = float(np.mean(e**2))
    return {'MSE': mse, 'RMSE': math.sqrt(mse), 'MAE': float(np.mean(abs(e))),
            'R2': float(1 - np.sum(e**2) / np.sum((actual - actual.mean())**2)),
            'WAPE_pct': float(100 * np.sum(abs(e)) / np.sum(abs(actual)))}


def engineer(spark, aggregate_path):
    # Read CSV in JVM: avoids Python-worker compatibility issues on Windows.
    d = spark.read.option('header', True).schema(
        'timestamp string, energy double, households integer').csv(str(aggregate_path))
    d = d.withColumn('ts', F.to_timestamp('timestamp')).withColumn('t', F.unix_timestamp('ts'))
    # Exact-time joins instead of row shifts: missing intervals cannot shift lags.
    for n in (1, 48, 336):
        prev = d.select((F.col('t') + n * 1800).alias('join_t'), F.col('energy').alias(f'lag{n}'))
        d = d.join(prev, d.t == prev.join_t, 'left').drop('join_t')
    slot = F.hour('ts') * 2 + F.minute('ts') / 30
    dow = (F.dayofweek('ts') + 5) % 7  # Monday=0
    for name, value, period in [('slot', slot, 48), ('dow', dow, 7),
                                 ('year', F.dayofyear('ts'), 365)]:
        d = d.withColumn(name + '_sin', F.sin(value * 2 * math.pi / period))
        d = d.withColumn(name + '_cos', F.cos(value * 2 * math.pi / period))
    return d.withColumn('weekend', (dow >= 5).cast('double')).na.drop(subset=FEATURES)


def pipeline(kind, reg=0., alpha=0., depth=5):
    assembler = VectorAssembler(inputCols=FEATURES, outputCol='base_features')
    if kind == 'DTR':
        return Pipeline(stages=[assembler, DecisionTreeRegressor(
            featuresCol='base_features', labelCol='energy', maxDepth=depth,
            maxBins=32, minInstancesPerNode=10, seed=SEED)])
    return Pipeline(stages=[assembler,
        StandardScaler(inputCol='base_features', outputCol='scaled_features',
                       withMean=True, withStd=True),
        PolynomialExpansion(inputCol='scaled_features', outputCol='features', degree=2),
        LinearRegression(featuresCol='features', labelCol='energy',
                         regParam=reg, elasticNetParam=alpha, maxIter=200,
                         tol=1e-7, standardization=True, solver='auto')])


def score_model(model, frame):
    t = time.perf_counter()
    pred = model.transform(frame).select('timestamp', 'energy', 'prediction').orderBy('timestamp').toPandas()
    seconds = time.perf_counter() - t
    result = metrics(pred.energy.to_numpy(), pred.prediction.to_numpy())
    return result, seconds, pred


def run(args):
    base = Path(args.output).resolve()
    results, logs = base / 'results', base / 'logs'
    results.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.FileHandler(logs/'experiment.log', encoding='utf-8'),
                                  logging.StreamHandler(sys.stdout)], force=True)
    log = logging.getLogger('lcl')
    started = time.perf_counter()
    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    python_runner = sys.executable
    if os.name == 'nt':
        # Spark batch launchers do not consistently quote paths with spaces.
        os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')
        python_runner = 'python'
    os.environ.setdefault('PYSPARK_PYTHON', python_runner)
    os.environ.setdefault('PYSPARK_DRIVER_PYTHON', python_runner)
    # Avoid unquoted Python path detection in Spark's Windows batch launcher.
    os.environ.setdefault('SPARK_HOME', str(Path(pyspark.__file__).resolve().parent))
    spark = SparkSession.builder.master(args.master).appName('LCL-Replikasi-Parsial')\
        .config('spark.driver.memory', '4g').config('spark.sql.shuffle.partitions', '8')\
        .config('spark.sql.session.timeZone', 'UTC').config('spark.ui.enabled', 'false')\
        .config('spark.driver.host', '127.0.0.1').config('spark.driver.bindAddress', '127.0.0.1')\
        .config('spark.sql.adaptive.enabled', 'true').getOrCreate()
    spark.sparkContext.setLogLevel('ERROR')
    info = {'client_report_date': '2026-10-14', 'execution_timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'spark': spark.version,
            'java': spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
            'os': platform.platform(), 'logical_cpus': os.cpu_count(), 'master': args.master,
            'driver_memory': '4g', 'shuffle_partitions': 8, 'timezone': 'UTC',
            'seed': SEED, 'features': FEATURES, 'forecast_horizon_minutes': 30,
            'validation_start': '2013-09-01', 'test_start': '2013-11-01'}
    (results/'environment.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    if args.aggregate:
        aggregate_path = Path(args.aggregate).resolve()
        profile = json.loads((results/'profile.json').read_text()) if (results/'profile.json').exists() else {}
        log.info('Menggunakan agregat terverifikasi: %s', aggregate_path)
    else:
        root = Path(args.data_dir).resolve()
        all_files = sorted(root.glob('LCL-June2015v2_*.csv'), key=lambda p: int(p.stem.rsplit('_',1)[1]))
        files = all_files[:args.files]
        if not files:
            raise FileNotFoundError('CSV LCL tidak ditemukan: ' + str(root))
        manifest = [{'file':p.name, 'bytes':p.stat().st_size,
                     'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
        (results/'input_manifest.json').write_text(json.dumps(manifest, indent=2))
        schema = T.StructType([T.StructField(c,T.StringType()) for c in ['LCLid','tariff','datetime_raw','energy_raw']])
        raw = spark.read.option('header', True).schema(schema).csv([str(p) for p in files])
        d = raw.select(F.trim('LCLid').alias('LCLid'), F.trim('tariff').alias('tariff'),
                       F.expr('try_to_timestamp(trim(datetime_raw), "yyyy-MM-dd HH:mm:ss.SSSSSSS")').alias('ts'),
                       F.expr('try_cast(trim(energy_raw) as double)').alias('energy')).cache()
        prof = d.agg(F.count('*').alias('raw_rows'), F.countDistinct('LCLid').alias('raw_households'),
                     F.sum(F.col('energy').isNull().cast('int')).alias('null_energy'),
                     F.sum(F.col('ts').isNull().cast('int')).alias('null_timestamp'),
                     F.sum((F.col('energy') == 0).cast('int')).alias('zero_energy'),
                     F.sum((F.col('energy') < 0).cast('int')).alias('negative_energy'),
                     F.min('ts').alias('min_time'), F.max('ts').alias('max_time')).first().asDict()
        prof = {k:str(v) if isinstance(v, datetime) else v for k,v in prof.items()}
        prof['source_files'] = [p.name for p in files]
        prof['available_files'] = len(all_files)
        prof['available_bytes'] = sum(p.stat().st_size for p in all_files)
        prof['zero_policy'] = 'retain: no evidence that all zeros are faulty'
        prof['partition_scope'] = 'first files sorted numerically; not authentic settlement blocks'
        valid = d.filter(F.col('ts').isNotNull() & F.col('energy').isNotNull() &
                         (F.col('energy') >= 0) & F.col('tariff').isin('Std','ToU') &
                         (F.length('LCLid') > 0))
        y = valid.filter((F.col('ts') >= '2013-01-01') & (F.col('ts') < '2014-01-01'))
        # Only exact half-hour timestamps are eligible for the prediction grid.
        y = y.filter(F.minute('ts').isin(0,30) & (F.second('ts')==0))
        dedup = y.groupBy('LCLid','tariff','ts').agg(F.avg('energy').alias('energy')).cache()
        prof['year_valid_rows_before_dedup'] = y.count()
        prof['year_deduplicated_rows'] = dedup.count()
        prof['duplicates_collapsed'] = prof['year_valid_rows_before_dedup'] - prof['year_deduplicated_rows']
        expected = 365 * 48
        coverage = dedup.groupBy('LCLid','tariff').agg(F.countDistinct('ts').alias('intervals'))\
            .withColumn('coverage', F.col('intervals') / expected).orderBy('LCLid')
        cov = coverage.toPandas()
        cov.to_csv(results/'household_coverage.csv',index=False)
        eligible = cov[(cov.tariff=='Std') & (cov.coverage >= args.min_coverage)]
        selected = eligible.head(args.households).LCLid.tolist()
        if len(selected) < args.households:
            raise ValueError(f'Hanya {len(selected)} rumah Std memenuhi cakupan, diminta {args.households}. Tambah --files.')
        prof['cohort_selection'] = 'Std, coverage>=%.3f in 2013, first %d IDs lexicographically' % (args.min_coverage, args.households)
        prof['eligible_households'] = len(eligible)
        prof['cohort_ids'] = selected
        prof['cohort_size'] = len(selected)
        prof['selection_limitation'] = 'annual completeness uses future availability for retrospective cohort design'
        cohort = dedup.filter((F.col('tariff')=='Std') & F.col('LCLid').isin(selected)).cache()
        cohort.createOrReplaceTempView('cohort')
        hourly = spark.sql('SELECT hour(ts) hour, avg(energy) mean_kwh, count(*) records FROM cohort GROUP BY hour(ts) ORDER BY hour')
        monthly = spark.sql('SELECT month(ts) month, avg(energy) mean_kwh, count(*) records FROM cohort GROUP BY month(ts) ORDER BY month')
        weekend = spark.sql('SELECT CASE WHEN dayofweek(ts) IN (1,7) THEN "Weekend" ELSE "Hari kerja" END day_type, avg(energy) mean_kwh, count(*) records FROM cohort GROUP BY day_type')
        for name, frame in [('hourly_profile',hourly),('monthly_profile',monthly),('weekend_profile',weekend)]:
            frame.toPandas().to_csv(results/(name+'.csv'),index=False)
        ag = cohort.groupBy('ts').agg(F.sum('energy').alias('energy'), F.countDistinct('LCLid').alias('households'))
        prof['cohort_rows'] = cohort.count()
        prof['incomplete_aggregate_intervals'] = ag.filter(F.col('households') != len(selected)).count()
        aggregate = ag.filter(F.col('households')==len(selected)).select(
            F.date_format('ts','yyyy-MM-dd HH:mm:ss').alias('timestamp'), 'energy','households').orderBy('timestamp').toPandas()
        prof['complete_aggregate_intervals'] = len(aggregate)
        prof['expected_intervals_2013'] = expected
        prof['aggregate_mean_kwh'] = float(aggregate.energy.mean())
        prof['aggregate_max_kwh'] = float(aggregate.energy.max())
        prof['preprocessing_seconds'] = time.perf_counter()-started
        aggregate_path = results/'aggregate_2013.csv'
        aggregate.to_csv(aggregate_path,index=False)
        profile = prof
        (results/'profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
        cohort.unpersist(); dedup.unpersist(); d.unpersist()
        log.info('Praproses selesai: %d baris, %d rumah, %d interval lengkap', prof['raw_rows'],len(selected),len(aggregate))
    features = engineer(spark,aggregate_path).cache()
    train = features.filter(F.col('ts') < '2013-09-01').cache()
    val = features.filter((F.col('ts') >= '2013-09-01') & (F.col('ts') < '2013-11-01')).cache()
    test = features.filter(F.col('ts') >= '2013-11-01').cache()
    counts = {'engineered_rows':features.count(), 'train':train.count(), 'validation':val.count(), 'test':test.count()}
    (results/'split_counts.json').write_text(json.dumps(counts,indent=2))
    log.info('Pembagian kronologis %s', counts)
    grids = {'MPR':[(0.,0.,5)], 'Ridge':[(r,0.,5) for r in (0.001,0.01,0.1)],
             'Lasso':[(r,1.,5) for r in (0.001,0.01,0.1)],
             'ElasticNet':[(r,0.5,5) for r in (0.001,0.01)],
             'DTR':[(0.,0.,depth) for depth in (5,12)]}
    trials, best = [], {}
    for kind, grid in grids.items():
        for reg, alpha, depth in grid:
            t=time.perf_counter(); model=pipeline(kind,reg,alpha,depth).fit(train); fit=time.perf_counter()-t
            m,predict,_=score_model(model,val)
            trial={'model':kind,'regParam':reg,'elasticNetParam':alpha,'maxDepth':depth,
                   'validation_RMSE':m['RMSE'],'validation_R2':m['R2'],'fit_seconds':fit,'predict_seconds':predict}
            trials.append(trial)
            log.info('Validasi: %s',trial)
            if kind not in best or m['RMSE'] < best[kind]['validation_RMSE']:
                best[kind]=trial
    pd.DataFrame(trials).to_csv(results/'validation_trials.csv',index=False)
    # Test remains unseen until selection completes. Refit each selected variant on train+validation.
    fit_data = features.filter(F.col('ts') < '2013-11-01').cache()
    fit_data.count()
    output=[]
    preds = test.select('timestamp','energy','lag1','lag48','lag336').orderBy('timestamp').toPandas()
    for col,name in [('lag1','Persistence-30min'),('lag48','Seasonal-1day'),('lag336','Seasonal-1week')]:
        m=metrics(preds.energy.to_numpy(),preds[col].to_numpy())
        output.append({'model':name,**m,'fit_seconds':0.,'predict_seconds':0.,'regParam':None,'elasticNetParam':None,'maxDepth':None})
        preds[name]=preds[col]
    for kind, config in best.items():
        t=time.perf_counter()
        model=pipeline(kind,config['regParam'],config['elasticNetParam'],config['maxDepth']).fit(fit_data)
        fit=time.perf_counter()-t
        m,predict,pred=score_model(model,test)
        output.append({'model':kind,**m,'fit_seconds':fit,'predict_seconds':predict,
                       'regParam':config['regParam'],'elasticNetParam':config['elasticNetParam'],
                       'maxDepth':config['maxDepth'] if kind=='DTR' else None})
        preds=preds.merge(pred[['timestamp','prediction']].rename(columns={'prediction':kind}),on='timestamp',validate='one_to_one')
        log.info('Uji: %s RMSE=%.6f R2=%.6f',kind,m['RMSE'],m['R2'])
        if kind=='DTR':
            imp=dict(zip(FEATURES,model.stages[-1].featureImportances.toArray().tolist()))
            (results/'tree_importances.json').write_text(json.dumps(imp,indent=2))
            (results/'tree_debug.txt').write_text(model.stages[-1].toDebugString,encoding='utf-8')
        else:
            last=model.stages[-1]
            (results/(kind+'_parameters.json')).write_text(json.dumps({'coefficients':last.coefficients.toArray().tolist(),
                'intercept':last.intercept,'degree':2,'expanded_features':len(last.coefficients)},indent=2))
    table=pd.DataFrame(output).sort_values('RMSE')
    table.to_csv(results/'test_metrics.csv',index=False)
    preds.to_csv(results/'test_predictions.csv',index=False)
    (results/'selected_configs.json').write_text(json.dumps(best,indent=2))
    log.info('Eksperimen selesai dalam %.2f detik',time.perf_counter()-started)
    (results/'run_summary.json').write_text(json.dumps({'total_seconds':time.perf_counter()-started,
        'best_test_model':table.iloc[0]['model'],'selection_criterion':'validation RMSE per model family',
        'test_protocol':'rolling one-step, observed past loads available at each forecast origin',
        'zero_policy':'retained','timing_protocol':'one run, warm JVM, includes transform+collect, not benchmark'},indent=2))
    spark.stop()
    return table


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',default='../Partitioned LCL Data/Small LCL Data')
    p.add_argument('--output',default='.')
    p.add_argument('--files',type=int,default=3)
    p.add_argument('--households',type=int,default=50)
    p.add_argument('--min-coverage',type=float,default=0.98)
    p.add_argument('--master',default='local[2]')
    p.add_argument('--aggregate',help='CSV agregat untuk mengulang ML tanpa CSV mentah')
    args=p.parse_args()
    print(run(args).to_string(index=False))


if __name__=='__main__':
    main()
