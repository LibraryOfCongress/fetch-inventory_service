"""Pure predicates for whether a container satisfies shelving prerequisites.

Legacy containers (trays / non-tray items imported via the seed loaders) are
created with ``scanned_for_accession`` / ``scanned_for_verification`` set ``True``
but no ``accession_job_id`` / ``verification_job_id`` — they predate the in-app
accession & verification workflows and were never processed by a job. The
``scanned_*`` flag is therefore the source of truth; the associated job's
completion status is only enforced when the container actually references a job.
"""


def passes_job_gate(*, scanned: bool, job_id, job, completed_status) -> bool:
    """Return True if a container clears an accession/verification gate.

    - Not scanned at all -> never passes.
    - Scanned with no job reference (legacy item) -> passes.
    - Scanned with a job reference -> the referenced job must exist and be
      in the ``completed_status`` state.
    """
    if not scanned:
        return False
    if job_id is None:
        return True
    return job is not None and job.status == completed_status
