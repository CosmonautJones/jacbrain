import hashlib;
import from graph.model { Evidence, EvidenceKind, KnowledgeGraph, RelationKind }
import from graph.walkers { UpsertEvidence, LinkEvidence }

def record(evidence_id: str, kind: EvidenceKind, content: str, jac_version: str = "0.37.23", project_id: str = "sample") -> Evidence {
    return Evidence(evidence_id=evidence_id, kind=kind, content=content,
        source_uri="sample://" + evidence_id,
        source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        jac_version=jac_version, project_id=project_id);
}

"""Synthetic evidence, not a recorded compiler execution. All nodes remain transient."""
def sample_graph() -> KnowledgeGraph {
    brain = KnowledgeGraph();
    for rec in [
        record("task", EvidenceKind.Task, "Explain why a typed edge requires endpoint declarations."),
        record("diagnostic", EvidenceKind.Diagnostic, "Example E2086: edge endpoint declaration is missing."),
        record("fix", EvidenceKind.Fix, "Declare edge Uses: Symbol --> Symbol {}"),
        record("concept", EvidenceKind.Concept, "Typed edges constrain endpoints and infer traversal result types."),
        record("document", EvidenceKind.Document, "Bundled jac-node-edge-patterns guide describes typed endpoints."),
        record("symbol", EvidenceKind.Symbol, "edge Uses: Symbol --> Symbol {}"),
        record("pattern", EvidenceKind.Pattern, "Prefer explicit typed endpoints over any-to-any edges.")
    ] { brain spawn UpsertEvidence(rec=rec); }
    for (source, target, relation) in [
        ("task", "diagnostic", RelationKind.produced),
        ("task", "fix", RelationKind.depends_on),
        ("fix", "diagnostic", RelationKind.fixes),
        ("fix", "concept", RelationKind.depends_on),
        ("document", "concept", RelationKind.documents),
        ("symbol", "concept", RelationKind.depends_on),
        ("pattern", "task", RelationKind.used_in)
    ] {
        brain spawn LinkEvidence(source_id=source, target_id=target,
            project_id="sample", jac_version="0.37.23", relation=relation);
    }
    return brain;
}
