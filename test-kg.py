from KGbuilder import KnowledgeGraph
kg = KnowledgeGraph()
kg.build_from_electrolytes_file(r"E:\Py_Projects\MAterial\KG-LLM4AD\KnowledgeGraph\pdf_test\electrolytes.json")
kg.export_to_json(r"E:\Py_Projects\MAterial\KG-LLM4AD\KnowledgeGraph\pdf_test\kg_output.json")
kg.visualize_kg(r"E:\Py_Projects\MAterial\KG-LLM4AD\KnowledgeGraph\pdf_test\kg.html")