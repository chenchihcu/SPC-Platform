\# AI\_ANALYSIS\_PROMPT\_STANDARD.md

\## Standard Prompt Structure for SPI/SPC Engineering Analysis



This document defines how AI agents should analyze

SPI/SPC statistical results and produce engineering reports.



The objective is to ensure that AI-generated conclusions

are consistent, traceable, and engineering-oriented.



\---



\# 1. Analysis Objective



AI must interpret SPI statistical results

to support SMT process engineers.



Typical goals:



• detect abnormal process behavior  

• identify possible root causes  

• classify defect types  

• recommend corrective actions  



The analysis must rely on:



SPC\_RULES.md  

SPI\_PROCESS\_RULES.md  

SPI\_DEFECT\_CLASSIFICATION.md  

SPI\_PARAMETER\_MODEL.md  



\---



\# 2. Required Input Data



AI analysis requires:



Statistical outputs



Mean  

Standard deviation  

Control limits  

Capability index (Cp, Cpk)



SPI measurements



Volume  

Height  

Area  

Offset



Optional context



Stencil thickness  

Component type  

PCB region  



\---



\# 3. Standard Analysis Structure



Every AI analysis report must follow this structure.



\### 1 Process Overview



Describe the dataset.



Example:



• number of boards analyzed  

• number of pads measured  

• measurement types included  



\---



\### 2 Statistical Summary



Provide statistical indicators.



Example:



Mean volume  

Standard deviation  

Capability index  



Explain whether the process

is stable or unstable.



\---



\### 3 SPC Interpretation



Interpret control chart behavior.



Examples:



Points outside control limits  

Process drift  

Trend patterns  



Explain what the pattern means.



\---



\### 4 Defect Classification



Identify potential defects.



Examples:



Insufficient paste  

Excess paste  

Offset printing  

Bridge risk  



Reference rules defined in:



SPI\_DEFECT\_CLASSIFICATION.md



\---



\### 5 Spatial Analysis (if available)



If coordinate data exists:



Analyze defect distribution across PCB.



Examples:



Edge concentration  

Corner clustering  

Printer alignment bias  



\---



\### 6 Process Risk Evaluation



Classify risk level.



Example levels:



Low risk



Process stable.



Medium risk



Minor variation.



High risk



Immediate investigation required.



\---



\### 7 Possible Root Causes



Suggest engineering explanations.



Examples:



Stencil clogging  

Printer misalignment  

Paste viscosity change  

Cleaning frequency too long  



These suggestions must reference

SPI\_PROCESS\_RULES.md.



\---



\### 8 Recommended Actions



Provide practical recommendations.



Examples:



Increase stencil cleaning frequency  

Adjust printer alignment  

Replace solder paste batch  

Check stencil wear  



Actions must be engineering-oriented.



\---



\# 4. Output Format



AI must generate structured reports.



Example format:



Process Overview



Statistical Summary



SPC Interpretation



Defect Classification



Risk Evaluation



Possible Root Causes



Recommended Actions



\---



\# 5. Engineering Language



AI responses must use

engineering terminology.



Avoid vague statements such as:



"Looks abnormal"



Instead use:



"Volume variation exceeds 3σ control limits."



\---



\# 6. Uncertainty Handling



If data is insufficient:



AI must explicitly state:



"Insufficient data for reliable SPC analysis."



Do not fabricate conclusions.



\---



\# 7. Safety Rule



AI must never modify statistical formulas

or reinterpret SPC definitions.



All statistical calculations must follow:



SPC\_RULES.md

