import from graph.model { Evidence, EvidenceKind, KnowledgeGraph, Contains, Relation, RelationKind, validate_record }

"""Identity is (project_id, jac_version, evidence_id). Changed evidence loses promotion."""
walker UpsertEvidence {
    has rec: Evidence;
    has result: Evidence | None = None;
    can locate with KnowledgeGraph entry {
        validate_record(self.rec);
        visit [item for item in [here ->:Contains:->] if
            item.evidence_id == self.rec.evidence_id and
            item.project_id == self.rec.project_id and
            item.jac_version == self.rec.jac_version] else {
            self.rec.promoted = False;
            here +>:Contains():+> self.rec;
            visit self.rec;
        }
    }
    can update with Evidence entry {
        if here.kind != self.rec.kind { raise ValueError("Cannot change an evidence kind in place"); }
        if here.content != self.rec.content or here.source_hash != self.rec.source_hash or here.source_uri != self.rec.source_uri {
            here.promoted = False;
        }
        if here.kind == EvidenceKind.Validation {
            for dependent in [here ->:Relation:->] { dependent.promoted = False; }
        }
        here.content = self.rec.content;
        here.source_uri = self.rec.source_uri;
        here.source_hash = self.rec.source_hash;
        here.validation_target_hash = self.rec.validation_target_hash;
        here.validation_status = self.rec.validation_status;
        self.result = here;
    }
}

walker LinkEvidence {
    has source_id: str, target_id: str, project_id: str, jac_version: str;
    has relation: RelationKind;
    has target: Evidence | None = None;
    has linked: bool = False;
    can locate with KnowledgeGraph entry {
        targets = [item for item in [here ->:Contains:->] if item.evidence_id == self.target_id and
            item.project_id == self.project_id and item.jac_version == self.jac_version];
        sources = [item for item in [here ->:Contains:->] if item.evidence_id == self.source_id and
            item.project_id == self.project_id and item.jac_version == self.jac_version];
        if not targets or not sources { raise ValueError("Both endpoints must exist in the requested project and version"); }
        self.target = targets[0];
        visit sources;
    }
    can connect with Evidence entry {
        target = self.target;
        if target is None { raise ValueError("Missing target"); }
        if self.relation == RelationKind.validates and here.kind != EvidenceKind.Validation {
            raise ValueError("Only Validation evidence can validate another record");
        }
        if target not in [here ->:Relation:kind == self.relation:->] {
            here +>:Relation(kind=self.relation):+> target;
        }
        self.linked = True;
    }
}

"""Outgoing bounded breadth-first context. Wrong project/version nodes are traversal barriers."""
walker TaskContext {
    has task_id: str, project_id: str, jac_version: str;
    has max_nodes: int = 20, max_depth: int = 2;
    has matches: list[Evidence] = [], depths: dict[str, int] = {};
    has reports: list[list[Evidence]] = [];
    can start with KnowledgeGraph entry {
        if self.max_nodes < 1 or self.max_nodes > 100 or self.max_depth < 0 or self.max_depth > 5 {
            raise ValueError("Use 1..100 nodes and 0..5 hops");
        }
        seeds = [item for item in [here ->:Contains:->] if item.evidence_id == self.task_id and
            item.kind == EvidenceKind.Task and item.project_id == self.project_id and item.jac_version == self.jac_version];
        if seeds { self.depths[seeds[0].evidence_id] = 0; visit seeds; }
    }
    can collect with Evidence entry {
        if here.project_id != self.project_id or here.jac_version != self.jac_version { skip; }
        self.matches.append(here);
        depth = self.depths[here.evidence_id];
        if depth >= self.max_depth { skip; }
        for neighbor in [here ->:Relation:->] {
            if len(self.depths) >= self.max_nodes { break; }
            if neighbor.project_id == self.project_id and neighbor.jac_version == self.jac_version and neighbor.evidence_id not in self.depths {
                self.depths[neighbor.evidence_id] = depth + 1;
                visit neighbor;
            }
        }
    }
    can finish with KnowledgeGraph exit { report self.matches; }
}

"""Promotion requires a passing validation for this exact source hash and toolchain."""
walker PromoteEvidence {
    has evidence_id: str, project_id: str, jac_version: str;
    has promoted: bool = False;
    can locate with KnowledgeGraph entry {
        visit [item for item in [here ->:Contains:->] if item.evidence_id == self.evidence_id and
            item.project_id == self.project_id and item.jac_version == self.jac_version];
    }
    can promote with Evidence entry {
        here.promoted = False;
        for proof in [here <-:Relation:kind == RelationKind.validates:<-] {
            if proof.kind == EvidenceKind.Validation and proof.project_id == here.project_id and proof.jac_version == here.jac_version and proof.validation_status == "passed" and proof.validation_target_hash == here.source_hash {
                here.promoted = True;
                self.promoted = True;
                break;
            }
        }
    }
}
