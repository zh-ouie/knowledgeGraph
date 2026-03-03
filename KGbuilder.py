import os
import json
import re
import networkx as nx
from pyvis.network import Network
import warnings
from typing import Dict, Any, List
warnings.filterwarnings('ignore')


class KnowledgeGraph:
    def __init__(self, reactions: Dict[str, Any] = None, properties: Dict[str, Any] = None):
        """
        KnowledgeGraph 类：
        - 不把文章题目作为节点（paper 节点被忽略）
        - 构建 system 节点，polymer/salt/solvent/temperature/conductivity 等为节点
        """
        self.properties = properties if properties is not None else {}
        self.reactions = reactions if reactions is not None else {}
        self.G = nx.DiGraph()
        self.chemical_substances = set()

    # ---------- helpers for parsing ----------
    @staticmethod
    def _parse_scientific_number(s: str):
        if not s or not isinstance(s, str):
            return None
        s = s.replace('×', 'x').replace('−', '-').replace('–', '-').replace('·', '.')
        # 2.7 x 10^-4 / 2.7x10-4
        m = re.search(r'([0-9]+(?:[.,][0-9]+)?)\s*[xX]?\s*10\^?([\-+]?\d+)', s)
        if m:
            base = m.group(1).replace(',', '.')
            exp = int(m.group(2))
            try:
                return float(base) * (10 ** exp)
            except Exception:
                return None
        # e notation or plain
        s2 = s.replace(' ', '').replace(',', '.')
        m2 = re.search(r'([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)', s2)
        if m2:
            try:
                return float(m2.group(1))
            except Exception:
                return None
        return None

    @staticmethod
    def _parse_system_text_block(block: str) -> List[Dict[str, Any]]:
        """
        把单个 LLM 原始文本解析成若干系统条目列表，
        每个条目包含 polymer_name, salt_name, solvent_type, solvent_fraction, temperature_C, electrolyte (原始字符串)
        """
        entries = []
        parts = re.split(r'Polymer\s*Electrolyte\s*\d*\s*[:\n]', block, flags=re.IGNORECASE)
        if len(parts) <= 1:
            parts = [block]
        for p in parts:
            text = p.strip()
            if not text:
                continue
            entry = {}
            for m in re.finditer(r'([a-zA-Z0-9_ \-]+)\s*:\s*(.+)', text):
                k = m.group(1).strip().lower().replace(' ', '_')
                v = m.group(2).strip()
                entry[k] = v
            normalized = {
                "polymer_name": entry.get("polymer_name") or entry.get("polymer") or None,
                "salt_name": entry.get("salt_name") or entry.get("salt") or None,
                "solvent_type": entry.get("solvent_type") or entry.get("solvent") or None,
                "solvent_fraction": entry.get("solvent_fraction") or entry.get("solvent_fraction") or None,
                "temperature_C": None,
                "electrolyte": entry.get("electrolyte") or entry.get("conductivity") or None,
            }
            t = entry.get("temperature_C") or entry.get("temperature")
            if t:
                try:
                    normalized["temperature_C"] = float(re.search(r'[-+]?[0-9]*\.?[0-9]+', t.replace(',', '.')).group(0))
                except Exception:
                    normalized["temperature_C"] = None
            normalized["conductivity_value"] = KnowledgeGraph._parse_scientific_number(normalized["electrolyte"]) if normalized["electrolyte"] else None
            normalized["conductivity_unit"] = None
            if normalized["electrolyte"]:
                u = re.search(r'(S\/cm|mS\/cm|S·cm-1|S cm-1|mS cm-1)', normalized["electrolyte"], re.IGNORECASE)
                if u:
                    normalized["conductivity_unit"] = u.group(1)
            entries.append(normalized)
        return entries

    # ---------- build KG from electrolytes json ----------
    def build_from_electrolytes_file(self, json_path: str, source_label_field: str = None):
        """
        从 electrolytes.json 构建 KG。
        行为：
         - 忽略文章题目（不创建 paper 节点或在 id/label 中使用文章标题）
         - 若字段为空/null/none 则不创建对应节点
        json_path: 文件路径，格式如 pdf_test/electrolytes.json
        """
        def _is_valid_field(v):
            if v is None:
                return False
            s = str(v).strip()
            if s == "":
                return False
            if s.lower() in {"null", "none", "nan"}:
                return False
            return True

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.G = nx.DiGraph()
        system_counter = 0

        for paper_key, content in data.items():
            systems = []
            if isinstance(content, dict):
                if "regex_extracted" in content and isinstance(content["regex_extracted"], list):
                    systems = content["regex_extracted"]
                elif "llm_raw" in content and isinstance(content["llm_raw"], str):
                    systems = self._parse_system_text_block(content["llm_raw"])
                elif isinstance(content, list):
                    systems = content
            elif isinstance(content, str):
                systems = self._parse_system_text_block(content)

            for sys_entry in systems:
                system_counter += 1
                sys_label = f"system::{system_counter}"
                self.G.add_node(sys_label, type="system", label=f"system_{system_counter}")

                # polymer
                poly = sys_entry.get("polymer_name")
                if _is_valid_field(poly):
                    poly_node = f"poly::{poly}"
                    if poly_node not in self.G:
                        self.G.add_node(poly_node, type="polymer", label=poly)
                    self.G.add_edge(sys_label, poly_node, label="has_polymer")
                    self.chemical_substances.add(poly)

                # salt
                salt = sys_entry.get("salt_name")
                if _is_valid_field(salt):
                    salt_node = f"salt::{salt}"
                    if salt_node not in self.G:
                        self.G.add_node(salt_node, type="salt", label=salt)
                    self.G.add_edge(sys_label, salt_node, label="has_salt")
                    self.chemical_substances.add(salt)

                # solvent
                solvent = sys_entry.get("solvent_type")
                if _is_valid_field(solvent):
                    parts = re.split(r'[;,/()\|]+', str(solvent))
                    for s in parts:
                        s2 = s.strip()
                        if not _is_valid_field(s2):
                            continue
                        sol_node = f"solvent::{s2}"
                        if sol_node not in self.G:
                            self.G.add_node(sol_node, type="solvent", label=s2)
                        self.G.add_edge(sys_label, sol_node, label="has_solvent")
                        self.chemical_substances.add(s2)

                # solvent fraction
                sf = sys_entry.get("solvent_fraction")
                if _is_valid_field(sf):
                    sf_node = f"solvent_frac::{sf}"
                    if sf_node not in self.G:
                        self.G.add_node(sf_node, type="property", label=str(sf))
                    self.G.add_edge(sys_label, sf_node, label="solvent_fraction")

                # temperature
                temp = sys_entry.get("temperature_C")
                if _is_valid_field(temp):
                    try:
                        temp_val = float(temp)
                        temp_node = f"temp::{temp_val}C"
                        if temp_node not in self.G:
                            self.G.add_node(temp_node, type="temperature", label=f"{temp_val} C")
                        self.G.add_edge(sys_label, temp_node, label="temperature")
                    except Exception:
                        temp_node = f"temp::{str(temp)}"
                        if temp_node not in self.G:
                            self.G.add_node(temp_node, type="temperature", label=str(temp))
                        self.G.add_edge(sys_label, temp_node, label="temperature")

                # conductivity
                cond_val = sys_entry.get("conductivity_value")
                cond_raw = sys_entry.get("electrolyte") or sys_entry.get("conductivity")
                if _is_valid_field(cond_raw) or (cond_val is not None):
                    if cond_val is not None:
                        label = f"{cond_val}"
                    else:
                        label = str(cond_raw)
                    if _is_valid_field(label):
                        cond_node = f"conductivity::{label}"
                        if cond_node not in self.G:
                            self.G.add_node(cond_node, type="conductivity", label=label)
                        self.G.add_edge(sys_label, cond_node, label="has_conductivity")

        return self

    # ---------- export with labels ----------
    def export_to_json(self, file_path: str):
        """
        Export nodes and edges to JSON, preserving edge labels.
        """
        node_mapping = {node: idx + 1 for idx, node in enumerate(self.G.nodes)}
        nodes = []
        for node, attrs in self.G.nodes(data=True):
            nodes.append({
                "id": node_mapping[node],
                "name": attrs.get("label", node),
                "key": node,
                "type": attrs.get("type", "")
            })

        links = []
        for u, v, data in self.G.edges(data=True):
            links.append({
                "source": node_mapping[u],
                "target": node_mapping[v],
                "label": data.get("label", "")
            })

        graph_data = {"nodes": nodes, "links": links}
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

    def count_nodes(self) -> int:
        return self.G.number_of_nodes()

    def visualize_kg(self, html_name: str = "KG.html"):
        net = Network(notebook=True, height="750px", width="100%", directed=True)
        for node, attrs in self.G.nodes(data=True):
            label = attrs.get("label", node)
            ntype = attrs.get("type", "")
            color = 'lightblue'
            if ntype in {'polymer', 'salt', 'solvent'}:
                color = 'pink'
            elif ntype == 'conductivity':
                color = 'lightgreen'
            elif ntype == 'temperature':
                color = 'orange'
            net.add_node(node, label=label, title=label, color=color)
        for u, v, data in self.G.edges(data=True):
            net.add_edge(u, v, label=data.get("label", ""), color='gray')
        net.set_options("""
        var options = {
          "physics": {
            "repulsion": {
              "centralGravity": 0.0,
              "springLength": 200,
              "springConstant": 0.05,
              "nodeDistance": 200,
              "damping": 0.09
            },
            "minVelocity": 0.75
          }
        }
        """)
        net.show(html_name)