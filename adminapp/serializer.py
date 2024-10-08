from rest_framework import serializers
from .models import Department, BlogAdditionalImage, Blogs, CancelBooking
from doctors.models import Doctor, Booking, Notification
from doctors.serializer import DoctorSerializer


class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department
        fields = "__all__"


class DoctorSerializer(serializers.ModelSerializer):
    doc_email = serializers.EmailField(required=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=True
    )

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
    doctor = DoctorSerializer()

    class Meta:
        model = Booking
        fields = "__all__"


class CancelBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancelBooking
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
