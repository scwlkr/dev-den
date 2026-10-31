export function downloadPDF(text, id) {
  const { jsPDF } = window.jspdf,
    pdf = new jsPDF({ unit: "mm", format: "a4" });
  pdf.setFont("helvetica");
  const clean = text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/…/g, "...")
    .replace(/[^\x09\x0a\x0d\x20-\x7e]/g, " ")
    .replace(/\\([*_\[\]<>`])/g, "$1");
  const lines = clean.split("\n");
  let y = 20;
  const pageHeight = 297;
  const bottom = 282;
  const drawHeader = () => {
    pdf.setFontSize(12);
    pdf.text("Den of Devs - decision report", 18, 12);
    pdf.setFontSize(9);
    pdf.text("Session " + id, 18, 16);
    pdf.setFontSize(10);
  };
  drawHeader();
  for (const line of lines) {
    const wrapped = pdf.splitTextToSize(line || " ", 174);
    for (const part of wrapped) {
      if (y > bottom) {
        pdf.addPage();
        y = 20;
        drawHeader();
      }
      pdf.text(part, 18, y);
      y += 4.8;
    }
  }
  const total = pdf.getNumberOfPages();
  for (let i = 1; i <= total; i++) {
    pdf.setPage(i);
    pdf.setFontSize(8);
    pdf.text("Page " + i + " of " + total, 18, pageHeight - 8);
  }
  pdf.save(id + ".pdf");
}