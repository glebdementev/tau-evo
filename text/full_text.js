const fs = require('fs');
const path = require('path');
const { Document, Packer } = require('docx');

const F = 'Times New Roman', S = 24;

// Import chapter children arrays
const litReviewChildren = require('./lit_review_source');
const methodologyChildren = require('./gen_methodology_v2');

// Combine all chapters in order
const allChildren = [
  ...litReviewChildren,
  ...methodologyChildren,
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: F, size: S } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: F }, paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: F }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: F }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: allChildren,
  }]
});

const outPath = path.join(__dirname, 'full_thesis.docx');
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`Done: ${outPath}`);
});
