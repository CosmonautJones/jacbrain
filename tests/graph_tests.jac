import from graph.model { EvidenceKind, KnowledgeGraph, Contains, Relation, RelationKind }
import from graph.sample { record, sample_graph }
import from graph.walkers { UpsertEvidence, LinkEvidence, TaskContext, PromoteEvidence }

test "upsert is idempotent and changes revoke promotion" {
    brain = KnowledgeGraph();
    first = record("fix", EvidenceKind.Fix, "first");
    brain spawn UpsertEvidence(rec=first);
    first.promoted = True;
    brain spawn UpsertEvidence(rec=record("fix", EvidenceKind.Fix, "updated"));
    items = [brain ->:Contains:->];
    assert len(items) == 1;
    assert items[0].content == "updated";
    assert not items[0].promoted;
}

test "context respects budget depth cycles and toolchain" {
    brain = sample_graph();
    old = record("old", EvidenceKind.Concept, "stale", jac_version="0.37.22");
    brain spawn UpsertEvidence(rec=old);
    items = [brain ->:Contains:->];
    task_item = items[0];
    task_item +>:Relation(kind=RelationKind.depends_on):+> old;
    brain spawn LinkEvidence(source_id="concept", target_id="task", project_id="sample",
        jac_version="0.37.23", relation=RelationKind.used_in);
    result = brain spawn TaskContext(task_id="task", project_id="sample", jac_version="0.37.23", max_nodes=3);
    assert len(result.matches) == 3;
    assert "old" not in [item.evidence_id for item in result.matches];
    shallow = brain spawn TaskContext(task_id="task", project_id="sample", jac_version="0.37.23", max_depth=0);
    assert len(shallow.matches) == 1;
    full = brain spawn TaskContext(task_id="task", project_id="sample", jac_version="0.37.23", max_depth=5);
    assert len(full.matches) == 4;
}

test "promotion requires a passing validation tied to exact source" {
    brain = KnowledgeGraph();
    candidate = record("fix", EvidenceKind.Fix, "candidate");
    proof = record("check", EvidenceKind.Validation, "synthetic test proof");
    proof.validation_status = "passed";
    proof.validation_target_hash = "0" * 64;
    brain spawn UpsertEvidence(rec=candidate);
    brain spawn UpsertEvidence(rec=proof);
    brain spawn LinkEvidence(source_id="check", target_id="fix", project_id="sample", jac_version="0.37.23", relation=RelationKind.validates);
    stale = brain spawn PromoteEvidence(evidence_id="fix", project_id="sample", jac_version="0.37.23");
    assert not stale.promoted;
    proof.validation_target_hash = candidate.source_hash;
    current = brain spawn PromoteEvidence(evidence_id="fix", project_id="sample", jac_version="0.37.23");
    assert current.promoted;
    failed_proof = record("check", EvidenceKind.Validation, "failed updated proof");
    failed_proof.validation_status = "failed";
    failed_proof.validation_target_hash = candidate.source_hash;
    brain spawn UpsertEvidence(rec=failed_proof);
    assert not candidate.promoted;
    failed = brain spawn PromoteEvidence(evidence_id="fix", project_id="sample", jac_version="0.37.23");
    assert not failed.promoted;
}

test "link rejects missing endpoints and deduplicates" {
    brain = sample_graph();
    with testraises(ValueError) {
        brain spawn LinkEvidence(source_id="missing", target_id="task", project_id="sample", jac_version="0.37.23", relation=RelationKind.depends_on);
    }
    brain spawn LinkEvidence(source_id="task", target_id="fix", project_id="sample", jac_version="0.37.23", relation=RelationKind.depends_on);
    items = [brain ->:Contains:->];
    assert len([edge items[0] ->:Relation:->]) == 2;
}

test "invalid records and unsafe budgets are rejected" {
    brain = KnowledgeGraph();
    rec = record("bad", EvidenceKind.Concept, "example");
    rec.source_hash = "not a digest";
    with testraises(ValueError) { brain spawn UpsertEvidence(rec=rec); }
    with testraises(ValueError) {
        brain spawn TaskContext(task_id="task", project_id="sample", jac_version="0.37.23", max_nodes=101);
    }
    assert len([brain ->:Contains:->]) == 0;
}

test "project and version identities remain separate" {
    brain = KnowledgeGraph();
    a = record("same", EvidenceKind.Task, "current");
    b = record("same", EvidenceKind.Task, "older", jac_version="0.37.22");
    c = record("same", EvidenceKind.Task, "other project", project_id="other");
    for item in [a, b, c] { brain spawn UpsertEvidence(rec=item); }
    a +>:Relation(kind=RelationKind.depends_on):+> c;
    context = brain spawn TaskContext(task_id="same", project_id="sample", jac_version="0.37.23");
    assert len([brain ->:Contains:->]) == 3;
    assert len(context.matches) == 1;
    assert context.matches[0].content == "current";
}
