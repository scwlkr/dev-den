export function downloadPDF(text, id) {
  const { jsPDF } = window.jspdf,
    pdf = new jsPDF({ unit: "mm", format: "a4" });
  pdf.setFont("helvetica");
  pdf.setFontSize(10);
  let y = 18;
  const clean = text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/…/g, "...")
    .replace(/[^\x09\x0a\x0d\x20-\x7e]/g, " ")
    .replace(/\\([*_\[\]<>`])/g, "$1");
  for (const line of clean.split("\n")) {
    const wrapped = pdf.splitTextToSize(line, 174);
    for (const part of wrapped) {
      if (y > 279) {
        pdf.addPage();
        y = 18;
      }
      pdf.text(part, 18, y);
      y += 4.8;
    }
  }
  pdf.save(id + ".pdf");
}
