import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework import serializers

from channels_api.decorators import action
from channels_api.generics import GenericAsyncWebsocketAPIView
from channels_api.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin, PatchModelMixin, DeleteModelMixin)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_generic_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        @action()
        def test_sync_action(self, pk=None):
            user = self.get_object(pk=pk)

            s = self.get_serializer(
                action_kwargs={'pk': pk},
                instance=user
            )
            return s.data, 200

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "test_sync_action",
            "pk": 2,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
            "action": "test_sync_action",
            "errors": ["Not found"],
            "response_status": 404,
            "request_id": 1,
            "data": None,
        }

    user = get_user_model().objects.create(
        username='test1', email='test@example.com'
    )

    pk = user.id

    assert get_user_model().objects.filter(pk=pk).exists()

    await communicator.disconnect()

    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()

    assert connected

    await communicator.send_json_to(
        {
            "action": "test_sync_action",
            "pk": pk,
            "request_id": 2
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "test_sync_action",
        "errors": [],
        "response_status": 200,
        "request_id": 2,
        "data": {'email': 'test@example.com', 'id': 1, 'username': 'test1'}
    }

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_create_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(CreateModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "create",
            "data": {
                "username": "test101",
                "email": "42@example.com"
            },
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()
    user = get_user_model().objects.all().first()

    assert user
    pk = user.id

    assert response == {
        "action": "create",
        "errors": [],
        "response_status": 201,
        "request_id": 1,
        "data": {'email': '42@example.com', 'id': pk, 'username': 'test101'}
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_list_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(ListModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "list",
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "list",
        "errors": [],
        "response_status": 200,
        "request_id": 1,
        "data": []
    }

    u1 = get_user_model().objects.create(
        username='test1', email='42@example.com'
    )
    u2 = get_user_model().objects.create(
        username='test2', email='45@example.com'
    )

    await communicator.send_json_to(
        {
            "action": "list",
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "list",
        "errors": [],
        "response_status": 200,
        "request_id": 1,
        "data": [
            {'email': '42@example.com', 'id': u1.id, 'username': 'test1'},
            {'email': '45@example.com', 'id': u2.id, 'username': 'test2'}
        ]
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_retrieve_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(RetrieveModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": 100,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    u1 = get_user_model().objects.create(
        username='test1', email='42@example.com'
    )
    u2 = get_user_model().objects.create(
        username='test2', email='45@example.com'
    )

    # lookup a pk that is not there
    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": u1.id - 1,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    # lookup up u1
    await communicator.send_json_to(
        {
            "action": "retrieve",
            "pk": u1.id,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "retrieve",
        "errors": [],
        "response_status": 200,
        "request_id": 1,
        "data": {
            'email': '42@example.com', 'id': u1.id, 'username': 'test1'
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_update_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(UpdateModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "update",
            "pk": 100,
            "data": {
                "username": "test101",
                "email": "42@example.com"
            },
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    u1 = get_user_model().objects.create(
        username='test1', email='42@example.com'
    )
    get_user_model().objects.create(
        username='test2', email='45@example.com'
    )

    await communicator.send_json_to(
        {
            "action": "update",
            "pk": u1.id,
            "data": {
                "username": "test101",
            },
            "request_id": 2
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 2,
        "data": {'email': '42@example.com', 'id': u1.id, 'username': 'test101'}
    }

    u1 = get_user_model().objects.get(id=u1.id)
    assert u1.username == 'test101'
    assert u1.email == '42@example.com'


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_patch_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(PatchModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "patch",
            "pk": 100,
            "data": {
                "username": "test101",
                "email": "42@example.com"
            },
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "patch",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    u1 = get_user_model().objects.create(
        username='test1', email='42@example.com'
    )
    get_user_model().objects.create(
        username='test2', email='45@example.com'
    )

    await communicator.send_json_to(
        {
            "action": "patch",
            "pk": u1.id,
            "data": {
                "email": "00@example.com",
            },
            "request_id": 2
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "patch",
        "errors": [],
        "response_status": 200,
        "request_id": 2,
        "data": {'email': '00@example.com', 'id': u1.id, 'username': 'test1'}
    }

    u1 = get_user_model().objects.get(id=u1.id)
    assert u1.username == 'test1'
    assert u1.email == '00@example.com'


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_delete_mixin_view():

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ('id', 'username', 'email',)

    class AView(DeleteModelMixin, GenericAsyncWebsocketAPIView):
        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

    assert not get_user_model().objects.all().exists()

    # Test a normal connection
    communicator = WebsocketCommunicator(AView, "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "action": "delete",
            "pk": 100,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "delete",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    u1 = get_user_model().objects.create(
        username='test1', email='42@example.com'
    )
    get_user_model().objects.create(
        username='test2', email='45@example.com'
    )

    await communicator.send_json_to(
        {
            "action": "delete",
            "pk": u1.id - 1,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "delete",
        "errors": ["Not found"],
        "response_status": 404,
        "request_id": 1,
        "data": None
    }

    await communicator.send_json_to(
        {
            "action": "delete",
            "pk": u1.id,
            "request_id": 1
        }
    )

    response = await communicator.receive_json_from()

    assert response == {
        "action": "delete",
        "errors": [],
        "response_status": 204,
        "request_id": 1,
        "data": None
    }

    assert not get_user_model().objects.filter(id=u1.id).exists()