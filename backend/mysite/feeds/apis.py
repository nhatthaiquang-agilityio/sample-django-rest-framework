from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, status, generics, mixins
from rest_framework.authentication import (
    SessionAuthentication, TokenAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from feeds.models import Feed, Comment, Emotion
from feeds.paginations import FeedPagination
from feeds.permissions import IsCommentOwner
from feeds.serializers import (
    FeedSerializer, CommentSerializer, EmotionSerializer)
from commons.paginations import CommonPagination

from .utils import get_feed


# Generic Views
class FeedList(generics.ListCreateAPIView):
    queryset = Feed.objects.select_related(
        'user').prefetch_related('emotion').all()
    serializer_class = FeedSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter,)
    pagination_class = FeedPagination

    def post(self, request, *args, **kwargs):
        serializer = FeedSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedDetail(APIView):
    """
    Retrieve, update or delete a feed instance
    """
    queryset = Feed.objects.select_related(
        'user').prefetch_related('emotion').all()
    authentication_classes = (
        SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk, format=None):
        feed = get_object_or_404(Feed, pk=pk)
        serializer = FeedSerializer(feed)
        return Response(serializer.data)


# Generic Views
class CommentList(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter,)
    pagination_class = CommonPagination

    # create a comment
    # It works
    # def post(self, request, *args, **kwargs):
    #     serializer = CommentSerializer(data=request.data)

    #     # get feed
    #     feed = get_feed(request.data['feed_id'])

    #     if serializer.is_valid():
    #         serializer.save(user=request.user, feed=feed)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # It works
    # def create(self, request, *args, **kwargs):
    #     serializer = CommentSerializer(data=request.data)

    #     # get feed
    #     feed = get_feed(request.data['feed_id'])

    #     if serializer.is_valid():
    #         serializer.save(user=request.user, feed=feed)
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)

    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # it works
    def perform_create(self, serializer):
        """
        create a comment
        """
        feed_id = self.kwargs.get('pk')

        # check feed exist
        feed = get_feed(feed_id)

        serializer.save(user=self.request.user, feed=feed)

    def get_queryset(self):
        return self.queryset.select_related(
            'feed', 'feed__user').prefetch_related(
                'feed__emotion').filter(feed_id=self.kwargs.get('pk'))


class CommentDetail(APIView):
    """
    Retrieve, update or delete a comment instance
    """
    authentication_classes = (
        SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated, IsCommentOwner)

    def get_queryset(self):
        return self.queryset.select_related(
            'feed', 'feed__user').prefetch_related(
                'feed__emotion').filter(id=self.kwargs.get('pk'))

    def get(self, request, pk, format=None):
        comment = self.queryset.select_related(
            'feed', 'feed__user').prefetch_related(
                'feed__emotion').get(pk=pk)
        serializer = CommentSerializer(comment)
        return Response(serializer.data)

    # Update comment
    def put(self, request, pk, format=None):
        comment = get_object_or_404(Comment, pk=pk)
        serializer = CommentSerializer(comment, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmotionList(generics.ListCreateAPIView):
    queryset = Emotion.objects.all()
    serializer_class = EmotionSerializer
    # lookup_url_kwarg = "pk"

    def perform_create(self, serializer):
        feed_id = self.kwargs.get('pk')

        # check feed exist
        feed = get_feed(feed_id)

        emotion = serializer.save(user=self.request.user)

        feed.emotion.add(emotion)
        feed.save()


class EmotionDetail(
        mixins.DestroyModelMixin,
        mixins.UpdateModelMixin,
        generics.GenericAPIView):
    queryset = Emotion.objects.all()
    serializer_class = EmotionSerializer
    lookup_field = "id"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        id = self.kwargs["id"]
        feed_id = self.kwargs["pk"]
        return Emotion.objects.get(id=id, feed_id=feed_id)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        serializer = EmotionSerializer(data=request.data)

        feed_id = self.kwargs.get('pk')
        emotion_id = self.kwargs.get('id')

        # check exist feed
        get_feed(feed_id)

        if serializer.is_valid():
            emotion = get_object_or_404(Emotion, pk=emotion_id)
            serializer.update(emotion, validated_data=request.data)

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        emotion_id = self.kwargs.get('id')
        feed_id = self.kwargs.get('pk')

        # check exist feed
        get_feed(feed_id)

        emotion = get_object_or_404(Emotion, pk=emotion_id)
        emotion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
