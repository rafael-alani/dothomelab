#!/usr/bin/env node
// Compare rendered source order with the same model used by the installed picker.
const fs = require('node:fs');
const model = require('./obsidian/model.cjs');
const [serverPath, uiPath] = process.argv.slice(2);
if (!serverPath || !uiPath) throw new Error('Usage: audit-ui-order.cjs SERVER_JSON UI_JSON');
const server = JSON.parse(fs.readFileSync(serverPath));
const ledger = server.ledger || server;
const ui = JSON.parse(fs.readFileSync(uiPath));
const collections = [...ledger.collections].sort((a, b) => a.source.localeCompare(b.source) ||
  a.ordinal - b.ordinal || a.id.localeCompare(b.id));
const lib = model.library({ collections, items: ledger.source_items, memberships: ledger.membership_entries });
const items = new Map(ledger.source_items.filter(i => i.source === 'yaay').map(i => [i.id, i.source_key]));
const unique = values => [...new Set(values)];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const roots = model.childCollections(lib, 'yaay').filter(c => c.id.startsWith('b:')).map(c => c.id.slice(2));
const report = { root_order_equal: same(ui.root_ids, roots), source_roots: ui.root_ids, picker_roots: roots,
  boards: [], sections: [] };
for (const board of ui.boards) {
  const childIds = model.childCollections(lib, 'yaay', board.id).map(c => c.id);
  report.boards.push({ id: board.id, title: collections.find(c => c.id === board.id)?.title,
    source_sections: board.section_order, picker_sections: childIds,
    section_order_equal: same(board.section_order, childIds), gaps: board.gaps });
  for (const section of board.sections) {
    if (!section.id) continue;
    const source = section.cards.map(card => {
      const keys = unique(card.ids.map(id => items.get(id)).filter(Boolean));
      return keys.length === 1 ? keys[0] : null;
    });
    const known = unique(source.filter(Boolean));
    const picker = model.browse(lib, 'yaay', section.id).map(p => p.key);
    const common = picker.filter(key => known.includes(key));
    const unknown = source.flatMap((key, index) => key === null ? [index] : []);
    report.sections.push({ id: section.id, title: section.title, board: board.id,
      source_order: source, picker_order: picker, unknown_positions: unknown,
      identities_equal: unknown.length ? null : same([...known].sort(), [...picker].sort()),
      order_equal: unknown.length ? null : same(known, picker),
      known_subsequence_equal: same(known, common) });
  }
}
report.summary = { boards: report.boards.length, sections: report.sections.length,
  board_section_order_mismatches: report.boards.filter(b => !b.section_order_equal).length,
  fully_identified_sections: report.sections.filter(s => !s.unknown_positions.length).length,
  section_post_order_mismatches: report.sections.filter(s => !s.known_subsequence_equal).length,
  unknown_card_positions: report.sections.reduce((n, s) => n + s.unknown_positions.length, 0) };
process.stdout.write(JSON.stringify(report));
