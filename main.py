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


from google.appengine.ext import ndb
import json
import webapp2
from webapp2 import Route, redirect

def qsToJson(query):
    items = []
    for item in query:
        item_d = item.to_dict()
        item_d['id'] = int(item.key.id())
        items.append(item_d)
    return items

def getEntity(response, model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            b_d = e.to_dict()
            b_d['id'] = int(e.key.id())
        else:
            b_d = {}
            response.status = 400
        response.write(json.dumps(b_d))
    else:
        entities = model.query()
        response.write(json.dumps(qsToJson(entities)))

def deleteEntity(response, model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            e.key.delete()
        else:
            response.status = 400
    else:
        entities = model.query()
        for e in entities:
            e.key.delete()

# inspired by - http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property

def patchEntity(response, patch, model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            e_d = e.to_dict()
            patch_d = json.loads(patch)
            # for key in e_d:
            #     if patch_d.get(key, None) is not None:
            #         e_d[key] = patch_d[key]
            for key in patch_d:
                if e_d.get(key, None) is not None:
                    e_d[key] = patch_d[key]
                elif key == 'id':
                    # Need to allow changing key?
                    pass
                else:
                    response.status = 400
                    return response
            e.populate(**e_d)
            e.put()
        else:
            response.status = 400

class Book(ndb.Model):
    title = ndb.StringProperty(required=True)
    isbn = ndb.StringProperty(required=True)
    genre = ndb.StringProperty(repeated=True)
    author = ndb.StringProperty(required=True)
    checkedIn = ndb.BooleanProperty()

class Customer(ndb.Model):
    name = ndb.StringProperty(required=True)
    balance = ndb.FloatProperty()
    checked_out = ndb.StringProperty(repeated=True)

class MainHandler(webapp2.RequestHandler):
    def get(self):
        books = Book.query()
        customers = Customer.query()
        all_json = {'books': qsToJson(books), 'customers': qsToJson(customers)}
        self.response.write(json.dumps(all_json))

    def delete(self):
        data = ndb.Query()
        for datum in data:
            datum.key.delete()

class BookHandler(webapp2.RequestHandler):
    def get(self, id=None):
        is_checked_in = self.request.get('checkedIn')
        if is_checked_in:
            print "blah"
            if is_checked_in == "true":
                is_checked_in = True
            elif is_checked_in == "false":
                is_checked_in = False
            books = Book.query(Book.checkedIn == is_checked_in)
            self.response.write(json.dumps(qsToJson(books)))
        else:
            getEntity(self.response, Book, id)

    def post(self):
        book_json = json.loads(self.request.body)
        book = Book(title=book_json['title'],
                    isbn=book_json['isbn'],
                    genre=book_json['genre'],
                    author=book_json['author'],
                    checkedIn=book_json.get('checkedIn', True))
        book.put()
        book_d = book.to_dict()
        book_d['id'] = book.key.id()
        self.response.status = 201
        self.response.write(json.dumps(book_d))

    def delete(self, id=None):
        deleteEntity(self.response, Book, id)
        # remove entity from checked out books
        if id:
            pass

    def patch(self, id):
        patchEntity(self.response, self.request.body, Book, id)
        # patch entity in checked out books if id (?)

class CustomerHandler(webapp2.RequestHandler):
    def get(self, id=None):
        getEntity(self.response, Customer, id)

    def getBooks(self, id):
        customer = ndb.Key(Customer, int(id)).get()
        full_books = []
        print customer.checked_out
        for book in customer.checked_out:
            b_id = book.split('/')[2]
            book = ndb.Key(Book, int(b_id)).get()
            b_d = book.to_dict()
            b_d['id'] = book.key.id()
            full_books.append(b_d)
        self.response.write(json.dumps(full_books))

    def post(self):
        customer_json = json.loads(self.request.body)
        # customer_id = getID(Customer)
        # customer_key = ndb.Key(Customer, customer_id)
        customer = Customer(name=customer_json['name'],
                            balance=customer_json.get('balance', None),
                            checked_out=customer_json.get('checked_out', []))
        customer.put()
        c_d = customer.to_dict()
        c_d['id'] = customer.key.id()
        self.response.status = 201
        self.response.write(json.dumps(c_d))

    def delete(self, id):
        deleteEntity(self.response, Customer, id)


    def patch(self, id):
        patchEntity(self.response, self.request.body, Customer, id)

class CheckoutHandler(webapp2.RequestHandler):
    def put(self, customer_id, book_id):
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        if customer is not None \
                and book is not None \
                and book.checkedIn:
            customer.checked_out.append("/books/{}".format(book.key.id()))
            customer.put()
            book.checkedIn = False
            book.put()
            self.response.status = 201
        else:
            self.response.status = 400

    def delete(self, customer_id, book_id):
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        books = customer.checked_out
        is_customers = False
        for b in books:
            if book_id == b.split('/')[2]:
                is_customers = True
        if customer is not None\
                and book is not None\
                and is_customers:
            customer.checked_out.remove("/books/{}".format(book_id))
            customer.put()
            book.checkedIn = True
            book.put()
        else:
            self.response.status = 400

    def get(self, customer_id, book_id):
        return redirect('/books/{}'.format(book_id))

# http://stackoverflow.com/questions/26433719/google-appengine-api-yaml-errors-eventlisteneryamlerror-mapping-values-are-not
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

app = webapp2.WSGIApplication([
    Route('/', handler=MainHandler, name='main'),
    Route('/books', handler=BookHandler, name='books'),
    Route('/books/<id:\d+>', handler=BookHandler, name='book'),
    Route('/customers', handler=CustomerHandler, name='customers'),
    Route('/customers/<id:\d+>', handler=CustomerHandler, name='customer'),
    Route('/customers/<id:\d+>/books', handler=CustomerHandler, name='customer books', handler_method='getBooks'),
    Route('/customers/<customer_id:\d+>/books/<book_id:\d+>', handler=CheckoutHandler, name='checkout book')
], debug=True)