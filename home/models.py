from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class Project(models.Model):
    # Icon choices tuple
    ICON_CHOICES = [
        ('fab fa-python', 'Python'),
        ('fab fa-js', 'JavaScript'),
        ('fab fa-react', 'React'),
        ('fab fa-angular', 'Angular'),
        ('fab fa-vue', 'Vue.js'),
        ('fab fa-node', 'Node.js'),
        ('fab fa-php', 'PHP'),
        ('fab fa-java', 'Java'),
        ('fab fa-html5', 'HTML5'),
        ('fab fa-css3', 'CSS3'),
        ('fab fa-sass', 'Sass'),
        ('fab fa-less', 'Less'),
        ('fab fa-wordpress', 'WordPress'),
        ('fab fa-laravel', 'Laravel'),
        ('fab fa-django', 'Django'),
        ('fab fa-docker', 'Docker'),
        ('fab fa-aws', 'AWS'),
        ('fab fa-github', 'GitHub'),
        ('fab fa-gitlab', 'GitLab'),
        ('fab fa-bitbucket', 'Bitbucket'),
        ('fas fa-database', 'Database'),
        ('fas fa-server', 'Server'),
        ('fas fa-code', 'Code'),
        ('fas fa-mobile-alt', 'Mobile'),
        ('fas fa-desktop', 'Desktop'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    link = models.URLField(blank=True)
    icon = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default='fab fa-python',
        help_text='Select a Font Awesome icon for your project'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'


class Post(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='posts')
    name = models.CharField(max_length=200)
    sub_heading = models.CharField(max_length=200)
    notes = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.post.name}'


class Rating(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stars = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']

    def __str__(self):
        return f'{self.stars} stars by {self.user.username} for {self.post.name}'


class SocialMediaContent(models.Model):
    PLATFORMS = (
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
    )

    CONTENT_TYPES = (
        ('dp', 'Profile Picture'),  # Instagram-specific
        ('post', 'Post'),
        ('reel', 'Reel'),          # Instagram-specific
        ('story', 'Story'),        # Instagram-specific
        ('video', 'Video'),        # Twitter/Facebook-specific
        ('image', 'Image'),        # Generic for all platforms
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORMS)
    url = models.URLField(max_length=500)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.platform.capitalize()} {self.content_type} from {self.url}"

    class Meta:
        ordering = ['-downloaded_at']