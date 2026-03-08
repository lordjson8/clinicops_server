from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from django.core.cache import cache

@receiver([post_save], sender=User)
def invalidate_current_user_cache(sender, instance, **kwargs):
    # print("Clearing Cache")
    cache.delete_pattern("*current_user*") 
