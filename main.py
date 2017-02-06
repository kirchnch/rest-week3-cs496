#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Course: cs496
# Assignment: REST Implementation
# Date: 02/05/16
# Username: kirchnch
# Name: Chris Kirchner
# Email: kirchnch@oregonstat.edu
# Description: a basic REST implementation of a library with customer and book resources

from google.appengine.ext import ndb
import json
import webapp2
from webapp2 import Route, redirect

def qsToJson(query):
    """
    converts query to list of python dictionaries representing json
    @param query: list of items queried
    @return: list of python dictionaries representing json
    """
    items = []
    for item in query:
        item_d = item.to_dict()
        # include id
        item_d['id'] = int(item.key.id())
        items.append(item_d)
    return items

def getEntity(response, model, id=None):
    """
    gets requested entity based on model and id
    @param response: response for resource delete request
    @param model: entity class
    @param id: resource identifier
    """
    if id:
        # get entity based on id
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            # convert entity to dict
            b_d = e.to_dict()
            b_d['id'] = int(e.key.id())
        # give bad response for non-existent book
        else:
            b_d = {}
            response.status = 400
        response.write(json.dumps(b_d))
    # get list if no id specified
    else:
        entities = model.query()
        response.write(json.dumps(qsToJson(entities)))


def deleteEntity(response, model, id=None):

    """
    deletes resource based on model and id
    @param response: response for resource delete request
    @param model: entity class
    @param id: resource identifier
    """

    if id:
        # get entity based on id
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            # delete entity
            e.key.delete()
        # give bad response if entity is non-existent
        else:
            response.status = 400
    # delete all entities of class if id not specified
    else:
        entities = model.query()
        for e in entities:
            e.key.delete()
            

# inspired by - http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property
def patchEntity(response, patch, model, id=None):
    """
    patches requested resource based on json patch, model, and id
    @param response: response for resource delete request
    @param patch: json containing fields to be patched
    @param model: entity class
    @param id: resource identifier
    @return: SUCCESS, unless patch request is malformed
    """

    if id:
        # get entity based on id
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            # convert entity to json
            e_d = e.to_dict()
            patch_d = json.loads(patch)
            # change each key in json patch
            for key in patch_d:
                if e_d.get(key, None) is not None:
                    e_d[key] = patch_d[key]
                elif key == 'id':
                    # Need to allow changing key?
                    pass
                # give bad response if json key is not recognized
                else:
                    response.status = 400
                    return response
            e.populate(**e_d)
            e.put()
        # give bad response if entity to be patched is non-existent
        else:
            response.status = 400


# book class model
class Book(ndb.Model):
    title = ndb.StringProperty(required=True)
    isbn = ndb.StringProperty(required=True)
    genre = ndb.StringProperty(repeated=True)
    author = ndb.StringProperty(required=True)
    checkedIn = ndb.BooleanProperty()


#customer class model
class Customer(ndb.Model):
    name = ndb.StringProperty(required=True)
    balance = ndb.FloatProperty()
    checked_out = ndb.StringProperty(repeated=True)


class MainHandler(webapp2.RequestHandler):

    def get(self):
        """
        returns all book and customer resource in main json object
        """
        books = Book.query()
        customers = Customer.query()
        all_json = {'books': qsToJson(books), 'customers': qsToJson(customers)}
        self.response.write(json.dumps(all_json))

    def delete(self):
        """
        deletes all book and customer resources
        """
        data = ndb.Query()
        for datum in data:
            datum.key.delete()


class BookHandler(webapp2.RequestHandler):

    def get(self, id=None):
        """
        gets requested list of books or book based on id
        @param id: book identifier
        """
        # check for REST query before
        is_checked_in = self.request.get('checkedIn')
        if is_checked_in:
            if is_checked_in == "true":
                is_checked_in = True
            elif is_checked_in == "false":
                is_checked_in = False
            # query for books with requested check in status
            books = Book.query(Book.checkedIn == is_checked_in)
            self.response.write(json.dumps(qsToJson(books)))
        # get resource(s) if no REST query
        else:
            getEntity(self.response, Book, id)

    def post(self):
        """
        adds new books based on json within body of request
        """
        book_json = json.loads(self.request.body)
        book = Book(title=book_json['title'],
                    isbn=book_json['isbn'],
                    genre=book_json['genre'],
                    author=book_json['author'],
                    checkedIn=book_json.get('checkedIn', True))
        book.put()
        book_d = book.to_dict()
        book_d['id'] = book.key.id()
        # respond with resource creation code
        self.response.status = 201
        self.response.write(json.dumps(book_d))

    def delete(self, id=None):
        """
        deletes all books or book based on id
        @param id: book identifier
        """
        deleteEntity(self.response, Book, id)
        # remove deleted entity from checked out books?
        if id:
            pass

    def patch(self, id):
        """
        patches book using json with body of request
        @param id: book identifier
        """
        patchEntity(self.response, self.request.body, Book, id)
        # patch entity in checked out books if id (?)


class CustomerHandler(webapp2.RequestHandler):

    def get(self, id=None):
        """
        gets the list of customers or customer based on id
        @param id: customer identifier
        """
        getEntity(self.response, Customer, id)

    def getBooks(self, id):
        """
        get list of books or book based on id
        @param id: books identifier
        """
        # gets customer based on id
        customer = ndb.Key(Customer, int(id)).get()
        full_books = []
        # compile dictionary list of checked out books
        for book in customer.checked_out:
            b_id = book.split('/')[2]
            book = ndb.Key(Book, int(b_id)).get()
            b_d = book.to_dict()
            b_d['id'] = book.key.id()
            full_books.append(b_d)
        self.response.write(json.dumps(full_books))

    def post(self):
        """
        post new customer based on json within body of request
        """
        customer_json = json.loads(self.request.body)
        # customer_id = getID(Customer)
        # customer_key = ndb.Key(Customer, customer_id)
        print customer_json
        customer = Customer(name=customer_json['name'],
                            balance=customer_json.get('balance', None),
                            checked_out=customer_json.get('checked_out', []))
        customer.put()
        c_d = customer.to_dict()
        c_d['id'] = customer.key.id()
        self.response.status = 201
        self.response.write(json.dumps(c_d))

    def delete(self, id=None):
        """
        deletes customers or customer based on id
        @param id: customer identifier
        """
        deleteEntity(self.response, Customer, id)
        # delete customer deletes books?


    def patch(self, id):
        """
        patches customer based on json in body of request
        @param id: customer identifier
        """
        patchEntity(self.response, self.request.body, Customer, id)


class CheckoutHandler(webapp2.RequestHandler):

    def put(self, customer_id, book_id):
        """
        checkouts book to customer based on their ids
        @param customer_id: customer identifier
        @param book_id: book identifier
        """
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        # make sure customer and book are existent
        if customer is not None \
                and book is not None \
                and book.checkedIn:
            # update customer's checked out list
            customer.checked_out.append("/books/{}".format(book.key.id()))
            customer.put()
            # set book checked in status
            book.checkedIn = False
            book.put()
            # signify resource "creation"
            self.response.status = 201
        # give bad response on non-existence
        else:
            self.response.status = 400

    def delete(self, customer_id, book_id):

        # delete customer deletes books?
        """
        checks in book from customer based on ids
        @param customer_id: customer identifier
        @param book_id: book identifier
        """
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        books = customer.checked_out
        # make sure book id is checked out by customer
        is_customers = False
        for b in books:
            if book_id == b.split('/')[2]:
                is_customers = True
        # make sure customer and book are existent
        if customer is not None\
                and book is not None\
                and is_customers:
            # remove book from checked out list
            customer.checked_out.remove("/books/{}".format(book_id))
            customer.put()
            # reset book checked in status
            book.checkedIn = True
            book.put()
        else:
            self.response.status = 400

    def get(self, customer_id, book_id):
        """
        gets books resource in customers checked out book by redirection
        @param customer_id: customer identifier
        @param book_id: book identifier
        @return: book resource in customer's list of checked out books
        """
        return redirect('/books/{}'.format(book_id))

# http://stackoverflow.com/questions/26433719/google-appengine-api-yaml-errors-eventlisteneryamlerror-mapping-values-are-not
# add patch method to webapp2
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

# URL route assignments
app = webapp2.WSGIApplication([
    Route('/', handler=MainHandler, name='main'),
    Route('/books', handler=BookHandler, name='books'),
    Route('/books/<id:\d+>', handler=BookHandler, name='book'),
    Route('/customers', handler=CustomerHandler, name='customers'),
    Route('/customers/<id:\d+>', handler=CustomerHandler, name='customer'),
    Route('/customers/<id:\d+>/books', handler=CustomerHandler, name='customer books', handler_method='getBooks'),
    Route('/customers/<customer_id:\d+>/books/<book_id:\d+>', handler=CheckoutHandler, name='checkout book')
], debug=True)