from rest_framework import serializers
from .models import Department, BlogAdditionalImage, Blogs
from doctors.models import Doctor, Booking


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class DoctorSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()

    class Meta:
        model = Doctor
        fields = "__all__"

    def to_representation(self, instance):

        representation = super().to_representation(instance)

        representation.pop("password", None)
        if instance.department:
            representation["department"] = instance.department.dept_name

        return representation


class BlogAdditionalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogAdditionalImage
        fields = "__all__"


class BlogsSerializer(serializers.ModelSerializer):
    additional_images = BlogAdditionalImageSerializer(many=True, required=False)
    image = serializers.ImageField(required=False)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Blogs
        fields = [
            "id",
            "title",
            "content",
            "author",
            "image",
            "date",
            "additional_images",
        ]


class AdminBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"
