from django.contrib import admin
from .models import Project, Category, Post, Comment, Rating, SocialMediaContent

admin.site.register(Project)
admin.site.register(Category)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Rating)
admin.site.register(SocialMediaContent)