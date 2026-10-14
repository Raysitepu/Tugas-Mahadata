"""Pemeriksaan konsistensi lintas artefak dan evaluasi independen dari Spark."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

root=Path(__file__).resolve().parents[1]/'results'
agg=pd.read_csv(root/'aggregate_2013.csv',parse_dates=['timestamp'])
pred=pd.read_csv(root/'test_predictions.csv',parse_dates=['timestamp'])
metrics=pd.read_csv(root/'test_metrics.csv')
trials=pd.read_csv(root/'validation_trials.csv')
config=json.loads((root/'selected_configs.json').read_text())
assert agg.timestamp.is_unique and pred.timestamp.is_unique
assert agg.timestamp.is_monotonic_increasing and pred.timestamp.is_monotonic_increasing
assert (agg.households==50).all() and (agg.energy>=0).all()
assert (pred.timestamp >= pd.Timestamp('2013-11-01')).all()
assert (pred.timestamp < pd.Timestamp('2014-01-01')).all()
indexed=agg.set_index('timestamp').energy
assert np.allclose(pred.energy,indexed.loc[pred.timestamp].to_numpy())
for n in (1,48,336):
    expected=indexed.reindex(pred.timestamp-pd.Timedelta(minutes=30*n)).to_numpy()
    assert np.isfinite(expected).all()
    assert np.allclose(pred[f'lag{n}'],expected)
for row in metrics.itertuples():
    y=pred.energy.to_numpy();p=pred[row.model].to_numpy();e=p-y
    assert np.isfinite(p).all()
    expect={'MSE':np.mean(e**2),'RMSE':np.sqrt(np.mean(e**2)),
            'MAE':np.mean(abs(e)),'R2':1-np.sum(e**2)/np.sum((y-y.mean())**2),
            'WAPE_pct':100*np.sum(abs(e))/np.sum(abs(y))}
    for name,value in expect.items():assert np.isclose(getattr(row,name),value,rtol=1e-10,atol=1e-10)
for model,choice in config.items():
    assert np.isclose(choice['validation_RMSE'],trials[trials.model==model].validation_RMSE.min())
out={'status':'passed','checks':['unique sorted timestamps','fixed 50-household nonnegative target',
    'test time boundaries','actual target matches aggregate','exact 30min/day/week lag matches',
    'all reported metrics independently recomputed','model-family selection minimizes validation RMSE'],
    'test_samples':len(pred),'models':len(metrics),'finite_predictions':True}
(root/'verification.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
