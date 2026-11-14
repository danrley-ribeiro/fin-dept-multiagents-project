"""Gera tema-referencia.pptx: o modelo padrão do pandoc com o tema do deck da DSM2.

O deck da DSM2 não tem os layouts que o pandoc procura ("Title Slide", "Title and Content"...), então ele
não serve direto como --reference-doc. Este script parte do modelo do próprio pandoc e copia do deck da DSM2
a paleta e as fontes (theme1.xml: clrScheme "SMA Material", Arial); títulos em azul-marinho (dk2), capa com
fundo azul-marinho e texto claro, corpo em 18 pt. Nada de cores fortes no conteúdo.

Uso (a partir da raiz): python entregas/dsm4/apresentacao/tema.py   (make apresentacao-dsm4 chama este script)
"""
from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DSM2 = AQUI.parents[1] / "dsm2" / "apresentacao" / "DSM2-apresentacao.pptx"
SAIDA = AQUI / "tema-referencia.pptx"


def main() -> int:
    base = subprocess.run(["pandoc", "--print-default-data-file", "reference.pptx"], check=True,
                          capture_output=True).stdout
    origem = AQUI / ".reference-pandoc.pptx"
    origem.write_bytes(base)
    with zipfile.ZipFile(DSM2) as z:
        tema_dsm2 = z.read("ppt/theme/theme1.xml").decode("utf-8")
    cores = re.search(r"<a:clrScheme .*?</a:clrScheme>", tema_dsm2, re.S).group(0)
    fontes = re.search(r"<a:fontScheme .*?</a:fontScheme>", tema_dsm2, re.S).group(0)

    with zipfile.ZipFile(origem) as zin, zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            dados = zin.read(item.filename)
            if item.filename == "ppt/theme/theme1.xml":
                t = dados.decode("utf-8")
                t = re.sub(r"<a:clrScheme .*?</a:clrScheme>", lambda _: cores, t, flags=re.S)
                t = re.sub(r"<a:fontScheme .*?</a:fontScheme>", lambda _: fontes, t, flags=re.S)
                dados = t.encode("utf-8")
            elif item.filename == "ppt/slideMasters/slideMaster1.xml":
                t = dados.decode("utf-8")
                titulo = re.search(r"<p:titleStyle>.*?</p:titleStyle>", t, re.S).group(0)
                novo = (titulo.replace('algn="ctr"', 'algn="l"').replace('sz="3300"', 'sz="2600"')
                        .replace('<a:schemeClr val="tx1"/>', '<a:schemeClr val="tx2"/>'))
                t = t.replace(titulo, novo)
                corpo = re.search(r"<p:bodyStyle>.*?</p:bodyStyle>", t, re.S).group(0)
                t = t.replace(corpo, corpo.replace('sz="2400"', 'sz="1700"').replace('sz="2100"', 'sz="1500"')
                              .replace('sz="1800"', 'sz="1400"'))
                dados = t.encode("utf-8")
            elif item.filename == "ppt/slideLayouts/slideLayout1.xml":  # "Title Slide": capa azul-marinho
                t = dados.decode("utf-8")
                t = t.replace('<p:cSld name="Title Slide">',
                              '<p:cSld name="Title Slide"><p:bg><p:bgPr><a:solidFill><a:schemeClr val="tx2"/>'
                              '</a:solidFill><a:effectLst/></p:bgPr></p:bg>', 1)
                t = t.replace("<a:lstStyle/>", '<a:lstStyle><a:lvl1pPr><a:defRPr><a:solidFill>'
                              '<a:schemeClr val="bg1"/></a:solidFill></a:defRPr></a:lvl1pPr></a:lstStyle>', 1)
                t = t.replace('<a:schemeClr val="tx1"><a:tint val="75000"/></a:schemeClr>', '<a:schemeClr val="bg1"/>')
                dados = t.encode("utf-8")
            zout.writestr(item, dados)
    origem.unlink()
    print(f"{SAIDA.name}: modelo do pandoc com a paleta e as fontes de {DSM2.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
