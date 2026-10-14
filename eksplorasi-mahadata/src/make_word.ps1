$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$markdown = Join-Path $root 'docs\Laporan_Eksplorasi_Mahadata.md'
$destination = Join-Path $root 'docs\123140047_Ray-Regan-Sitepu_Eksplorasi-Mahadata.docx'
$qaFolder = Join-Path $root 'tmp\word-qa'
New-Item -ItemType Directory -Path $qaFolder -Force | Out-Null
$word = $null
$doc = $null
$script:isCover = $true
$script:coverBlock = 0
$script:pagePending = $false
$script:isReferences = $false
$script:stepCount = 0
function Plain-Text([string]$text) {
    $text = $text.Replace('<br/>',"`v")
    $text = [regex]::Replace($text,'<[^>]+>','')
    return [System.Net.WebUtility]::HtmlDecode($text).Replace("`r`n","`v").Replace("`n","`v")
}
function Add-Paragraph([string]$text, [int]$style = -1, [string]$kind = 'body') {
    $plain = Plain-Text $text
    $start = $doc.Content.End - 1
    $range = $doc.Range($start,$start)
    $range.InsertAfter($plain + "`r")
    $p = $doc.Range($start,$start+$plain.Length+1).Paragraphs.Item(1)
    $p.Range.Style = $style
    $p.Range.Font.Reset()
    $p.Format.Reset()
    if ($script:pagePending) { $p.Format.PageBreakBefore = -1; $script:pagePending = $false }
    if ($kind -eq 'caption') {
        $p.Range.Font.Size = [single]9.5
        $p.Format.Alignment = 0
        $p.Format.SpaceBefore = 5
        $p.Format.SpaceAfter = 6
        $p.Format.KeepWithNext = -1
    } elseif ($kind -eq 'code') {
        $p.Range.Font.Name = 'Courier New'
        $p.Range.Font.Size = [single]8.5
        $p.Format.Alignment = 0
        $p.Format.LineSpacingRule = 4
        $p.Format.LineSpacing = 12
    } elseif ($kind -eq 'reference') {
        $p.Range.Font.Size = [single]9.5
        $p.Format.Alignment = 0
        $p.Format.LeftIndent = 13
        $p.Format.FirstLineIndent = -13
        $p.Format.SpaceAfter = 7
        $p.Format.LineSpacingRule = 4
        $p.Format.LineSpacing = 12
    }
    foreach ($tag in @('b','i')) {
        foreach ($match in [regex]::Matches($text,"<$tag>(.*?)</$tag>",[System.Text.RegularExpressions.RegexOptions]::Singleline)) {
            $part = Plain-Text $match.Groups[1].Value
            $offset = $plain.IndexOf($part,[System.StringComparison]::Ordinal)
            if ($offset -ge 0) {
                $r = $doc.Range($start+$offset,$start+$offset+$part.Length)
                if ($tag -eq 'b') { $r.Font.Bold = -1 } else { $r.Font.Italic = -1 }
            }
        }
    }
    return $p
}
function Add-Picture([string]$path,[double]$width,[bool]$cover) {
    $p = Add-Paragraph ''
    $p.Format.Alignment = 1
    $p.Format.LineSpacingRule = 0
    $p.Format.KeepWithNext = -1
    $p.Format.SpaceAfter = $(if ($cover) { 21 } else { 5 })
    $p.Format.SpaceBefore = $(if ($cover) { 8 } else { 0 })
    $anchor = $doc.Range($p.Range.Start,$p.Range.Start)
    $picture = $doc.InlineShapes.AddPicture($path,$false,$true,$anchor)
    $picture.LockAspectRatio = -1
    $picture.Width = $width
}
try {
    $word = New-Object -ComObject Word.Application
    if ($word.Documents.Count -ne 0) { throw 'Instance Word berisi dokumen lain; tidak digunakan.' }
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $doc = $word.Documents.Add()
    $doc.PageSetup.PageWidth = 595.28
    $doc.PageSetup.PageHeight = 841.89
    $doc.PageSetup.TopMargin = 59.53
    $doc.PageSetup.BottomMargin = 60.94
    $doc.PageSetup.LeftMargin = 85.04
    $doc.PageSetup.RightMargin = 75.12
    $doc.PageSetup.DifferentFirstPageHeaderFooter = -1
    $body = $doc.Styles.Item(-1)
    $body.Font.Name = 'Times New Roman'
    $body.Font.Size = 11
    $body.Font.Color = 0
    $body.ParagraphFormat.Alignment = 3
    $body.ParagraphFormat.SpaceAfter = 8
    $body.ParagraphFormat.SpaceBefore = 0
    $body.ParagraphFormat.KeepWithNext = 0
    $body.ParagraphFormat.PageBreakBefore = 0
    $body.ParagraphFormat.LineSpacingRule = 4
    $body.ParagraphFormat.LineSpacing = 13.2
    foreach ($id in @(-2,-3)) {
        $s = $doc.Styles.Item($id)
        $s.Font.Name = 'Times New Roman'
        $s.Font.Size = [single]$(if ($id -eq -2) { 13 } else { 11.5 })
        $s.Font.Bold = -1
        $s.Font.Color = 0
        $s.ParagraphFormat.Alignment = 0
        $s.ParagraphFormat.KeepWithNext = -1
        $s.ParagraphFormat.SpaceBefore = $(if ($id -eq -2) { 0 } else { 8 })
        $s.ParagraphFormat.SpaceAfter = $(if ($id -eq -2) { 11 } else { 7 })
    }
    $list = $doc.ListTemplates.Add($false,'ExperimentSteps')
    $list.ListLevels.Item(1).NumberFormat = '%1.'
    $list.ListLevels.Item(1).NumberStyle = 0
    $list.ListLevels.Item(1).StartAt = 1
    $list.ListLevels.Item(1).NumberPosition = 0
    $list.ListLevels.Item(1).TextPosition = 18
    $list.ListLevels.Item(1).TabPosition = 18
    $list.ListLevels.Item(1).Font.Name = 'Times New Roman'
    $blocks = [regex]::Split([System.IO.File]::ReadAllText($markdown),'(?:\r?\n){2,}')
    foreach ($block in $blocks) {
        $block = $block.Trim()
        if (-not $block) { continue }
        if ($block -eq '---') { $script:pagePending = $true; $script:isCover = $false; continue }
        if ($script:isCover) {
            $script:coverBlock++
            if ($block -eq 'Disusun oleh') { Add-Picture (Join-Path $root 'assets\it-era-reference-logo.png') 111.97 $true }
            $p = Add-Paragraph $block
            $p.Format.Alignment = 1
            $p.Format.LineSpacingRule = 4
            if ($script:coverBlock -eq 1) { $p.Range.Font.Size = 17; $p.Range.Font.Bold = -1; $p.Format.LineSpacing = 21; $p.Format.SpaceAfter = 18 }
            elseif ($script:coverBlock -eq 2) { $p.Range.Font.Size = 15; $p.Range.Font.Bold = -1; $p.Format.LineSpacing = 19; $p.Format.SpaceAfter = 15 }
            elseif ($script:coverBlock -eq 3) { $p.Range.Font.Size = 11; $p.Format.LineSpacing = 15; $p.Format.SpaceAfter = 12 }
            else { $p.Range.Font.Size = 12; $p.Range.Font.Bold = -1; $p.Format.LineSpacing = 16; $p.Format.SpaceAfter = 12 }
            if ($block.StartsWith('PROGRAM STUDI')) { $p.Format.SpaceBefore = 22 }
            continue
        }
        if ($block.StartsWith('## ')) { $null = Add-Paragraph $block.Substring(3) -3; continue }
        if ($block.StartsWith('# ')) {
            $title = $block.Substring(2)
            $script:isReferences = ($title -eq 'DAFTAR PUSTAKA')
            $null = Add-Paragraph $title -2
            continue
        }
        if ($block.StartsWith('| ')) {
            $lines = $block -split '\r?\n'
            $rows = @()
            foreach ($line in $lines) {
                if ($line -match '^\|\s*---') { continue }
                $rows += ,@(($line.Trim().Trim('|') -split '\|') | ForEach-Object { $_.Trim() })
            }
            $cols = $rows[0].Count
            $ratios = switch ($cols) {
                2 { if ($rows[0][0] -eq 'Keterbatasan') { @(.41,.59) } else { @(.32,.68) } }
                3 { if ($rows[0][0] -eq 'Jenis hari') { @(.25,.47,.28) } elseif ($rows[0][0] -eq 'Aspek') { @(.25,.37,.38) } else { @(.22,.42,.36) } }
                4 { @(.20,.28,.26,.26) }
                5 { @(.24,.18,.21,.18,.19) }
                6 { if ($rows[0][1] -eq 'Konfigurasi') { @(.17,.29,.15,.13,.13,.13) } elseif ($rows[0][1] -eq 'MSE') { @(.31,.14,.14,.14,.12,.15) } else { @(.24,.15,.16,.15,.13,.17) } }
            }
            $table = $doc.Tables.Add($doc.Range($doc.Content.End-1,$doc.Content.End-1),$rows.Count,$cols)
            $table.AllowAutoFit = $false
            $table.PreferredWidthType = 3
            $table.PreferredWidth = 435.12
            $table.TopPadding = 6
            $table.BottomPadding = 6
            $table.LeftPadding = 6
            $table.RightPadding = 6
            $table.Rows.AllowBreakAcrossPages = $false
            $table.Rows.SetLeftIndent(6,0)
            for ($c=1; $c -le $cols; $c++) { $table.Columns.Item($c).SetWidth((435.12*$ratios[$c-1]),0) }
            $table.Borders.Enable = 1
            for ($i=1; $i -le $rows.Count; $i++) {
                for ($c=1; $c -le $cols; $c++) { $table.Cell($i,$c).Range.Text = Plain-Text $rows[$i-1][$c-1] }
            }
            $table.Range.Font.Name = 'Times New Roman'
            $table.Range.Font.Size = [single]9.5
            $table.Range.ParagraphFormat.Alignment = 0
            $table.Range.ParagraphFormat.SpaceAfter = 0
            $table.Range.ParagraphFormat.SpaceBefore = 0
            $table.Range.ParagraphFormat.LineSpacingRule = 4
            $table.Range.ParagraphFormat.LineSpacing = 11.5
            $table.Range.ParagraphFormat.KeepWithNext = 0
            $table.Rows.Item(1).HeadingFormat = -1
            $table.Rows.Item(1).Range.Font.Bold = -1
            $table.Rows.Item(1).Shading.BackgroundPatternColor = 15592941
            continue
        }
        if ($block -match '^!\[(.*)\]\((.+)\)$') {
            $caption = $Matches[1]
            $imagePath = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $root 'docs') $Matches[2]))
            Add-Picture $imagePath 435.12 $false
            $null = Add-Paragraph $caption -1 'caption'
            continue
        }
        if ($block -match '^<b>\d+\. ') {
            $script:stepCount++
            $text = [regex]::Replace($block,'^<b>\d+\. ','<b>')
            $p = Add-Paragraph $text
            $p.Range.ListFormat.ApplyListTemplateWithLevel($list,($script:stepCount -gt 1),2,2,1)
            $p.Format.SpaceAfter = 8
            continue
        }
        $kind = 'body'
        if ($block.StartsWith('Tabel ')) { $kind = 'caption' }
        elseif ($block.StartsWith('python src/')) { $kind = 'code' }
        elseif ($script:isReferences) { $kind = 'reference' }
        $null = Add-Paragraph $block -1 $kind
    }
    $footer = $doc.Sections.Item(1).Footers.Item(1)
    $footer.Range.ParagraphFormat.Alignment = 1
    $footer.Range.Font.Name = 'Times New Roman'
    $footer.Range.Font.Size = 9
    $null = $footer.PageNumbers.Add(1,$false)
    $footer.PageNumbers.RestartNumberingAtSection = -1
    $footer.PageNumbers.StartingNumber = 0
    Write-Output 'Content and tables built. Saving DOCX...'
    # Persist native Word Open XML without the by-reference SaveAs COM binding.
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $flat = New-Object System.Xml.XmlDocument
    $flat.LoadXml([string]$doc.WordOpenXML)
    $ns = New-Object System.Xml.XmlNamespaceManager($flat.NameTable)
    $ns.AddNamespace('pkg','http://schemas.microsoft.com/office/2006/xmlPackage')
    $stream = [System.IO.File]::Open($destination,[System.IO.FileMode]::Create)
    $archive = New-Object System.IO.Compression.ZipArchive($stream,[System.IO.Compression.ZipArchiveMode]::Create)
    $types = New-Object System.Text.StringBuilder
    [void]$types.Append('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">')
    try {
        foreach ($part in $flat.SelectNodes('/pkg:package/pkg:part',$ns)) {
            $name = $part.GetAttribute('name','http://schemas.microsoft.com/office/2006/xmlPackage')
            $contentType = $part.GetAttribute('contentType','http://schemas.microsoft.com/office/2006/xmlPackage')
            [void]$types.Append('<Override PartName="' + [System.Security.SecurityElement]::Escape($name) + '" ContentType="' + [System.Security.SecurityElement]::Escape($contentType) + '"/>')
            $entry = $archive.CreateEntry($name.TrimStart('/'))
            $target = $entry.Open()
            try {
                $xml = $part.SelectSingleNode('pkg:xmlData',$ns)
                if ($xml) {
                    $text = $xml.FirstChild.OuterXml
                    if ($name -eq '/docProps/core.xml') {
                        $core = New-Object System.Xml.XmlDocument
                        $core.LoadXml($text)
                        $coreNs = New-Object System.Xml.XmlNamespaceManager($core.NameTable)
                        $coreNs.AddNamespace('dc','http://purl.org/dc/elements/1.1/')
                        $author = $core.SelectSingleNode('//dc:creator',$coreNs)
                        if ($author) { $author.InnerText = 'Ray Regan Sitepu' }
                        $text = $core.OuterXml
                    }
                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
                } else {
                    $bytes = [System.Convert]::FromBase64String($part.SelectSingleNode('pkg:binaryData',$ns).InnerText)
                }
                $target.Write($bytes,0,$bytes.Length)
            } finally { $target.Dispose() }
        }
        [void]$types.Append('</Types>')
        $entry = $archive.CreateEntry('[Content_Types].xml')
        $target = $entry.Open()
        try {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($types.ToString())
            $target.Write($bytes,0,$bytes.Length)
        } finally { $target.Dispose() }
    } finally { $archive.Dispose(); $stream.Dispose() }
    Write-Output 'DOCX saved. Rendering for verification...'
    $wordRenderPath = [string](Join-Path $qaFolder 'word-render.pdf')
    $doc.GetType().InvokeMember('ExportAsFixedFormat',[System.Reflection.BindingFlags]::InvokeMethod,$null,$doc,
        [object[]]@($wordRenderPath,17,$false,0,0,1,1,0,$false,$true,0,$true,$true,$false)) | Out-Null
    Write-Output ('DOCX: ' + $destination)
    Write-Output ('Pages in Word: ' + $doc.ComputeStatistics(2))
} finally {
    if ($doc) { $doc.Close(0); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null }
    if ($word) {
        if ($word.Documents.Count -eq 0) { $word.Quit() }
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
}
