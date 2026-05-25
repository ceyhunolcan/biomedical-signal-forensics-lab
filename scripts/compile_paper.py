"""Compile paper/manuscript.md and paper/supplement.md to docx with post-processing.

For each docx, runs:
  1. pandoc with citeproc + reference-doc styles
  2. Strip BlockText style from first 12 paragraphs (pandoc default that collapses
     paragraph spacing on the first paragraph after a heading)
  3. Apply cell-level booktabs table borders (top + header-bottom + bottom rules,
     no internal verticals)

Run:  python3 scripts/compile_paper.py
"""
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIB = ROOT / "paper" / "paper.bib"
REF = ROOT / "paper" / "reference_styled.docx"


def pandoc_compile(md_path, docx_path):
    subprocess.run([
        "pandoc", str(md_path),
        "--citeproc",
        f"--bibliography={BIB}",
        f"--reference-doc={REF}",
        "-o", str(docx_path),
    ], check=True)


def strip_block_text(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        with z.open("word/document.xml") as f:
            content = f.read().decode("utf-8")
    paras = re.findall(r"<w:p\b.*?</w:p>", content, re.DOTALL)
    new_content = content
    n_fixed = 0
    for p in paras[:12]:
        if '<w:pStyle w:val="BlockText"' in p:
            new_p = re.sub(r'<w:pStyle w:val="BlockText"\s*/>', "", p)
            new_p = re.sub(r"<w:pPr>\s*</w:pPr>", "", new_p)
            new_content = new_content.replace(p, new_p, 1)
            n_fixed += 1
    if n_fixed:
        tmp = docx_path.with_suffix(".tmp.docx")
        with zipfile.ZipFile(docx_path, "r") as zin:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.namelist():
                    data = zin.read(item)
                    if item == "word/document.xml":
                        data = new_content.encode("utf-8")
                    zout.writestr(item, data)
        shutil.move(str(tmp), str(docx_path))
    return n_fixed


def make_borders(top=False, bottom=False, top_sz=12, bottom_sz=8):
    parts = ["<w:tcBorders>"]
    parts.append(
        f'<w:top w:val="single" w:sz="{top_sz}" w:space="0" w:color="000000"/>'
        if top else '<w:top w:val="nil"/>'
    )
    parts.append('<w:left w:val="nil"/>')
    parts.append(
        f'<w:bottom w:val="single" w:sz="{bottom_sz}" w:space="0" w:color="000000"/>'
        if bottom else '<w:bottom w:val="nil"/>'
    )
    parts.append('<w:right w:val="nil"/>')
    parts.append("</w:tcBorders>")
    return "".join(parts)


def restyle_cell(cell_xml, border_xml):
    cell_xml = re.sub(r"<w:tcBorders>.*?</w:tcBorders>", "", cell_xml, flags=re.DOTALL)
    if "<w:tcPr>" in cell_xml:
        return cell_xml.replace("<w:tcPr>", "<w:tcPr>" + border_xml, 1)
    if "<w:tcPr/>" in cell_xml:
        return cell_xml.replace("<w:tcPr/>", "<w:tcPr>" + border_xml + "</w:tcPr>", 1)
    return re.sub(
        r"(<w:tc\b[^>]*>)",
        r"\1<w:tcPr>" + border_xml + "</w:tcPr>",
        cell_xml, count=1,
    )


def restyle_table(table_xml):
    rows = re.findall(r"<w:tr\b.*?</w:tr>", table_xml, re.DOTALL)
    if not rows:
        return table_xml
    n = len(rows)
    new_table = table_xml
    for i, row in enumerate(rows):
        if i == 0 and i == n - 1:
            border = make_borders(top=True, bottom=True, top_sz=12, bottom_sz=12)
        elif i == 0:
            border = make_borders(top=True, bottom=True, top_sz=12, bottom_sz=8)
        elif i == n - 1:
            border = make_borders(top=False, bottom=True, bottom_sz=12)
        else:
            border = make_borders(top=False, bottom=False)
        new_row = re.sub(
            r"<w:tc\b.*?</w:tc>",
            lambda m: restyle_cell(m.group(0), border),
            row, flags=re.DOTALL,
        )
        new_table = new_table.replace(row, new_row, 1)
    return new_table


def restyle_tables(docx_path):
    tmp = docx_path.with_suffix(".tmp.docx")
    n_tables = 0
    with zipfile.ZipFile(docx_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == "word/document.xml":
                    text = data.decode("utf-8")
                    text, n_tables = re.subn(
                        r"<w:tbl\b.*?</w:tbl>",
                        lambda m: restyle_table(m.group(0)),
                        text, flags=re.DOTALL,
                    )
                    data = text.encode("utf-8")
                zout.writestr(item, data)
    shutil.move(str(tmp), str(docx_path))
    return n_tables


def compile_doc(md_path, docx_path):
    pandoc_compile(md_path, docx_path)
    n_bt = strip_block_text(docx_path)
    n_t = restyle_tables(docx_path)
    print(f"  {docx_path.name}: BlockText stripped {n_bt}, tables restyled {n_t}")


if __name__ == "__main__":
    print("Compiling manuscript...")
    compile_doc(ROOT / "paper" / "manuscript.md", ROOT / "paper" / "manuscript.docx")
    sup_md = ROOT / "paper" / "supplement.md"
    if sup_md.exists():
        print("Compiling supplement...")
        compile_doc(sup_md, ROOT / "paper" / "supplement.docx")
    print("Done.")
