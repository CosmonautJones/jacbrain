enum EvidenceKind: str {
    Concept = "Concept", Document = "Document", Symbol = "Symbol",
    Diagnostic = "Diagnostic", Fix = "Fix", Pattern = "Pattern",
    Task = "Task", Validation = "Validation"
}

enum RelationKind: str {
    depends_on = "depends_on", documents = "documents", produced = "produced",
    fixes = "fixes", validates = "validates", used_in = "used_in"
}

node Evidence {
    has evidence_id: str, kind: EvidenceKind, content: str, source_uri: str;
    has source_hash: str, jac_version: str, project_id: str;
    has promoted: bool = False;
    has validation_target_hash: str = "", validation_status: str = "";
}

node KnowledgeGraph { has name: str = "JacBrain transient graph"; }

edge Contains: KnowledgeGraph --> Evidence {}
edge Relation: Evidence --> Evidence { has kind: RelationKind; }

def validate_record(rec: Evidence) {
    if not rec.evidence_id or not rec.source_uri or not rec.project_id or not rec.jac_version {
        raise ValueError("Evidence identity and provenance fields are required");
    }
    if len(rec.source_hash) != 64 or not all(ch in "0123456789abcdef" for ch in rec.source_hash) {
        raise ValueError("source_hash must be a lowercase SHA-256 digest");
    }
}
