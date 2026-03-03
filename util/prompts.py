                    
prompt_electrolyte_extraction_cot = """
Extract all distinct polymer electrolyte systems from the given content. 
Only extract polymer electrolyte where the value of ionic_conductivity is fully identified.

You must strictly adhere to the following rules:

1. A polymer electrolyte system must include at least one measured ionic_conductivity value .
2. Matrix_Material is the polymer name, for example PVA, PAM, Glass Fiber and so on.
3. ionic_conductivity (sigma): Convert scientific notation into float (e.g., 2.7 × 10⁻⁴ → 2.7e-4). Use units: S/cm  You must write down the value and unit simutaneously and strictly. For example, 2.7e-4 S/cm.
4. Test_termperature is the test temperature for conductivity, in °C strictly.
5. System_Type is Hydrogel or Liquid_Separator. Nothing except two is allowed to write.
6. Solvent_System usually filled in H2O, H2O/DMSO, H2O/EG and so on.
7. Electrolyte_Salt usually filled in KOH, ZnSO4, Zn(OTf)2 and so on. Try to make it as comprehensive as possible
8. Salt_Concentration: the unit of Salt_Concentration usually is M, e.g., 6M.
9. Filler_Additive_Type usually filled in GO, SiO2, MXene and so on.
10. Crosslinker_Type usually filled in MBAA, GA and so on. If it is diaphragm, fill in N/A.
11. Crosslinking_Degree is optional. If the system doesn't have it, fill in null.
12. Free_Bound_Water is Free_water or Bound_water. It is optional. If the system doesn't have it, fill in null.
13. The unit of Thickness is μm.
14. Liquid_Content_or_Uptake: If it is a hydrogel, fill in the water content; if it is a membrane, fill in the liquid absorption rate.
15. Support_Material: Porous/Fiber support. Fill in the material name, or null.
16. The unit of Tensile_Strength is MPa.
17. The unit of Elongation_at_Break is %.
18. Porous support: Fill in 1 if a porous framework exists, 0 if it does not.
19. Fiber skeleton: Fill in 1 if fiber reinforcement is present, 0 if not.
20. Operating_Temp_Range: The operating temperature range of this system, directly fill in the original descriptive text.The unit is °C.
21. Thermal_Decomposition_Temp_Td: The unit is °C.
22. Alkali_Stability_Performance: Extract the original descriptive text, and only fill it in when the literature explicitly tests the stability under alkaline conditions (KOH/NaOH, etc.). Otherwise, fill in null.
23. Tg_or_Phase_Transition_Temp: When filling it out, make sure to note whether it is the glass transition temperature or the phase transition temperature. The unit is ℃.
24. Transference_Number: T+.
25. Dendrite_Suppression: Fill in 1 if the system has the ability to suppress dendrites, otherwise enter 0.
26. Electrochemical_Window: The unit is V.
27. Rct: Rcl is the interface resistance.
28. Cdl: Cdl is a double-layer capacitor.
29. Cycle_Stability_Raw: Directly copy and paste the original long sentence, don't just fill in numbers.
30. For information not mentioned in the article, fill in as null; do not make things up.
31. For all information with units, both the unit and the value must be wrote down simutaneously and strictly.
32. If None of the polymer electrolyte systems are found, respond with "None". Do not write anything else.
33. There may be more than one conductivity value in the paper. Each conductivity value corresponds to a specific conductivity system. Extract all the conductivity systems and label them as Polymer Electrolyte 001, Polymer Electrolyte 002, Polymer Electrolyte 003, and so on.

Format the output strictly as follows:

Output:

Polymer Electrolyte 001:
Ionic_Conductivity:
Test_Temperature:
Article_Title:
DOI:
Year:
system_type: hydrogel or liquid_Separator
Matrix_Naterial: PVA or PAM or Glass Fiber or 
Solvent_System:
Electrolyte_Salt:
Salt_Concentration:
Filler_Additive_Type: GO or SiO2 or Mxene...
Filler_Additive_Content:
Crosslinker_Type: MBAA or GA ...,or N/A
Crosslinker_Content
Crosslinking_Degree (optional):
Key_Functional_Group:
Free_Bound_Water (optional):
Thickness: unit μm
Liquid_Content_or_Uptake:
Support_Material:
Tensile_Strength:
Elongation_at_Break:
Swelling_Ratio: 
Porous_support:
Fiber_skeleton:
Operating_Temp_Range:
Thermal_Decomposition_Temp_Td:
Alkali_Stability_Performance:
Tg_or_Phase_Transition_Temp:
Ion_Diffusion_Coeff:
Transference_Number:
Dendrite_Suppression:
Electrochemical_Window:
Rct:
Cdl:
Cycle_Stability_Raw:

Polymer Electrolyte 002:
...

"""

prompt_electrolyte_extraction = """
Extract all distinct polymer electrolyte systems from the given content. 
Only extract polymer electrolyte where all matrix_material and ionic_conductivity are fully identified. Exclude any electrolyte if any of them is unspecified.

You must strictly adhere to the following rules:

1. A polymer electrolyte system must include at least:
   - a matrix_material (polymer host),
   - and at least one measured conductivity value .
2. Only when BOTH ionic-conductivity and polymer_name are confirmed, construct the system.
    Exclude systems where any required dependency is missing:
   - No conductivity → system invalid.
   - No polymer_name → system invalid.
3. Matrix_Material is the polymer name, for example PVA, PAM, Glass Fiber and so on.
3.1. ionic_conductivity (sigma): Convert scientific notation into float (e.g., 2.7 × 10⁻⁴ → 2.7e-4). Use units: S/cm  
4. Test_termperature is the test temperature for conductivity, in °C strictly.
5. System_Type is Hydrogel or Liquid_Separator. Nothing except two is allowed to write.
6. Solvent_System usually filled in H2O, H2O/DMSO, H2O/EG and so on.
7. Electrolyte_Salt usually filled in KOH, ZnSO4, Zn(OTf)2 and so on. Try to make it as comprehensive as possible
8. Salt_Concentration: the unit of Salt_Concentration usually is M, e.g., 6M.
9. Filler_Additive_Type usually filled in GO, SiO2, MXene and so on.
10. Crosslinker_Type usually filled in MBAA, GA and so on. If it is diaphragm, fill in N/A.
11. Crosslinking_Degree is optional. If the system doesn't have it, fill in null.
12. Free_Bound_Water is Free_water or Bound_water. It is optional. If the system doesn't have it, fill in null.
13. The unit of Thickness is μm.
14. Liquid_Content_or_Uptake: If it is a hydrogel, fill in the water content; if it is a membrane, fill in the liquid absorption rate.
15. Support_Material: Porous/Fiber support. Fill in the material name, or null.
16. The unit of Tensile_Strength is MPa.
17. The unit of Elongation_at_Break is %.
18. Porous support: Fill in 1 if a porous framework exists, 0 if it does not.
19. Fiber skeleton: Fill in 1 if fiber reinforcement is present, 0 if not.
20. Operating_Temp_Range: The operating temperature range of this system, directly fill in the original descriptive text.The unit is °C.
21. Thermal_Decomposition_Temp_Td: The unit is °C.
22. Alkali_Stability_Performance: Extract the original descriptive text, and only fill it in when the literature explicitly tests the stability under alkaline conditions (KOH/NaOH, etc.). Otherwise, fill in null.
23. Tg_or_Phase_Transition_Temp: When filling it out, make sure to note whether it is the glass transition temperature or the phase transition temperature. The unit is ℃.
24. Transference_Number: T+.
25. Dendrite_Suppression: Fill in 1 if the system has the ability to suppress dendrites, otherwise enter 0.
26. Electrochemical_Window: The unit is V.
27. Rct: Rcl is the interface resistance.
28. Cdl: Cdl is a double-layer capacitor.
29. Cycle_Stability_Raw: Directly copy and paste the original long sentence, don't just fill in numbers.
30. For information not mentioned in the article, fill in as null; do not make things up.
31. For all information with units, both the unit and the value must be provided.

Format the output strictly as follows:

Output:

Polymer Electrolyte 001:
Ionic_Conductivity:
Test_Temperature:
Article_Title:
DOI:
Year:
system_type: hydrogel or liquid_Separator
Matrix_Naterial: PVA or PAM or Glass Fiber or 
Solvent_System:
Electrolyte_Salt:
Salt_Concentration:
Filler_Additive_Type: GO or SiO2 or Mxene...
Filler_Additive_Content:
Crosslinker_Type: MBAA or GA ...,or N/A
Crosslinker_Content
Crosslinking_Degree (optional):
Key_Functional_Group:
Free_Bound_Water (optional):
Thickness: unit μm
Liquid_Content_or_Uptake:
Support_Material:
Tensile_Strength:
Elongation_at_Break:
Swelling_Ratio: 
Porous_support:
Fiber_skeleton:
Operating_Temp_Range:
Thermal_Decomposition_Temp_Td:
Alkali_Stability_Performance:
Tg_or_Phase_Transition_Temp:
Ion_Diffusion_Coeff:
Transference_Number:
Dendrite_Suppression:
Electrochemical_Window:
Rct:
Cdl:
Cycle_Stability_Raw:

Polymer Electrolyte 002:
...

"""

