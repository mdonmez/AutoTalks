from pypdf import PdfWriter

merger = PdfWriter()

# DONT SUGGEST FOR HERE
# Sıra | Ad                 |
# ---- | ------------------ |
# 1    | META INTRO         |
# 2    | Hatice Hilal Aslan |
# 3    | Betül Aydoğ        |
# 4    | Yasin Efe Başer    |
# 5    | Nehir Oğunday      |
# 6    | Hacer Bayram       |
# 7    | Cüneyt Sinan Sevi  |
# 8    | Ezgi Karaaslan     |
# 9    | Efe Sağdıç         |
# 10   | Elif Barın         |
# 11   | META OUTRO         |

# DONT SUGGEST FOR HERE
pdf_files = [
    "pdfler/meta-intro.pdf",
    "pdfler/hilal-sunum.pdf",
    "pdfler/betul-sunum.pdf",
    "pdfler/yasin-sunum.pdf",
    "pdfler/nehir-sunum.pdf",
    "pdfler/hacer-sunum.pdf",
    "pdfler/cuneyt-sunum.pdf",
    "pdfler/ezgi-sunum.pdf",
    "pdfler/efe-sunum.pdf",
    "pdfler/elif-sunum.pdf",
    "pdfler/meta-outro.pdf",
]


for pdf in pdf_files:
    merger.append(pdf)

merger.write("meta-agl-talks-slide-2025.pdf")
merger.close()
