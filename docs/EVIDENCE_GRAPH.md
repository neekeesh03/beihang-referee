# Evidence graph

Every completed run emits `artifacts/evidence_graph.dot`.

The graph makes the decisive logic inspectable:

- evidence anchors → claims they support;
- concerns → claims they challenge;
- evidence anchors → concerns they ground;
- concerns → closure criteria.

This is useful for debugging reviewer drift: an apparently strong paragraph in the final review is not enough if the graph reveals that its evidence node is missing or points at a different claim.
