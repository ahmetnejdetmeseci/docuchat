from rest_framework import serializers

class UploadResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    files = serializers.ListField(child=serializers.CharField(), required=False)
