from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_delete

from AlgoliaSearch.models import AlgoliaIndex

from algoliasearch import algoliasearch


class AlgoliaEngineError(Exception):
    '''Something went wrong with Algolia engine.'''

class RegistrationError(AlgoliaEngineError):
    '''Something went wrong when registering a model with the search sengine.'''

class AlgoliaEngine(object):
    def __init__(self):
        '''Initializes Algolia engine.'''
        self.__registered_models = {}
        self.client = algoliasearch.Client(settings.ALGOLIA_APPLICATION_ID,
                                           settings.ALGOLIA_API_KEY)

    def is_registered(self, model):
        '''Checks whether the given models is registered with Algolia engine.'''
        return model in self.__registered_models

    def register(self, model, index_cls=AlgoliaIndex):
        '''
        Registers the given model with Algolia engine.

        If the given model is already registered with Algolia engine, a
        RegistrationError will be raised.
        '''
        # Check for existing registration
        if self.is_registered(model):
            raise RegistrationError('{} is already registered with Algolia engine'.format(
                model
            ))
        # Perform the registration.
        index_obj = index_cls(model, self.client)
        self.__registered_models[model] = index_obj
        # Connect to the signalling framework.
        post_save.connect(self.__post_save_receiver, model)
        pre_delete.connect(self.__pre_delete_receiver, model)

    def unregister(self, model):
        '''
        Unregisters the given model with Algolia engine.

        If the given model is not registered with Algolia engine, a
        RegistrationError will be raised.
        '''
        if not self.is_registered(model):
            raise RegistrationError('{} is not registered with Algolia engine'.format(
                model
            ))
        # Perform the unregistration.
        del self.__registered_models[model]
        # Disconnect fron the signalling framework.
        post_save.disconnect(self.__post_save_receiver, model)
        pre_delete.disconnect(self.__pre_delete_receiver, model)

    def get_registered_models(self):
        '''Returns a sequence of models that have been registered with Algolia engine.'''
        return list(self.__registered_models.keys())

    def get_adapter(self, model):
        '''Returns the adapter associated with the given model.'''
        if self.is_registered(model):
            return self.__registered_models[model]
        raise RegistrationError('{} is not registered with Algolia engine'.format(
            model
        ))

    def get_adapter_from_instance(self, instance):
        model = instance.__class__
        return self.get_adapter(model)

    def update_obj_index(self, obj):
        adapter = self.get_adapter_from_instance(obj)
        adapter.update_obj_index(obj)

    def delete_obj_index(self, obj):
        adapter = self.get_adapter_from_instance(obj)
        adapter.delete_obj_index(obj)

    # Signalling hooks.

    def __post_save_receiver(self, instance, **kwargs):
        '''Signal handler for when a registered model has been saved.'''
        self.update_obj_index(instance)

    def __pre_delete_receiver(self, instance, **kwargs):
        '''Signal handler for when a registered model has been deleted.'''
        self.delete_obj_index(instance)


# Algolia engine
algolia_engine = AlgoliaEngine()