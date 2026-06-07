\# SPI\_ANALYSIS\_WORKFLOW.md

\## SPI Data Analysis Workflow



This document defines the standard workflow

for SPI data analysis.



The workflow connects:



SPI measurements

SPC statistical analysis

defect classification

engineering interpretation.



\---



\# 1. Data Import



Load two primary datasets.



Measurement data



SPI inspection results.



Coordinate data



PCB pad positions.



\---



\# 2. Data Validation



Validate required fields.



Required fields:



RefDes

BoardNo

MeasurementValue



Optional fields:



Volume

Height

Area

Offset



Invalid records should be flagged.



\---



\# 3. Data Mapping



Map SPI measurement fields

to internal schema.



Example mapping:



SPI field → internal field



Volume → volume

Height → height

Area → area



Alias mapping may be required.



\---



\# 4. Data Join



Join measurement data with coordinate data.



Key:



RefDes



Result dataset:



RefDes

BoardNo

Volume

Height

Area

X

Y



\---



\# 5. Statistical Analysis



Perform SPC analysis.



Examples:



I-MR chart

Xbar-R chart



Compute:



Mean

Sigma

Control limits



\---



\# 6. Capability Analysis



If specification limits exist:



Compute:



Cp

Cpk

Pp

Ppk



Evaluate process capability.



\---



\# 7. Defect Classification



Use SPI defect rules to classify

each measurement.



Examples:



Insufficient

Excess

Offset

Bridge risk



Results may include:



Defect type

Severity level



\---



\# 8. Spatial Analysis



Project measurements onto PCB layout.



Generate:



Heatmap

Defect clusters



Identify:



Printer alignment issues

Stencil wear areas



\---



\# 9. Trend Analysis



Analyze process over time.



Example indicators:



Volume trend

Defect trend

Capability trend



This helps detect process drift.



\---



\# 10. Component-Level Analysis



Aggregate SPI data by component.



Metrics:



Mean volume

Defect ratio

Volume variation



Useful for identifying

component-specific printing issues.



\---



\# 11. Reporting



Generate engineering reports.



Examples:



Top defect components

Defect distribution

Process capability



Reports should support

engineering decision making.



\---



\# 12. Root Cause Support



SPI analysis should help identify:



Stencil clogging

Printer alignment issues

Paste aging

Environmental effects



The system should guide

engineers toward root cause analysis.



\---



\# 13. Continuous Monitoring



SPI data should support:



Real-time monitoring

historical analysis

trend tracking



This helps maintain stable

SMT printing processes.

