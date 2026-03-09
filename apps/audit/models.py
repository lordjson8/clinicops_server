
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        SENT      = "sent",      "Sent"
        FAILED    = "failed",    "Failed"
        REJECTED  = "rejected",  "Rejected"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient   = models.CharField(max_length=20)
    message     = models.TextField()
    sender_id   = models.CharField(max_length=50, blank=True)

    # AT response fields
    at_message_id = models.CharField(max_length=100, blank=True)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    cost          = models.CharField(max_length=20, blank=True)
    failure_reason = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # Optional: link to a patient/appointment
    # content_type  = models.ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    # object_id     = models.UUIDField(null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [models.Index(fields=["recipient", "status"])]