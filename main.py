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


def qsToJson(query):
    items = []
    for item in query:
        item_d = item.to_dict()
        item_d['id'] = int(item.key.id())
        # item_d['parent'] = item.key.parent()
        items.append(item_d)
    return items

def getEntity(response, model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            b_d = e.to_dict()
        else:
            b_d = {}
        response.write(json.dumps(b_d))
    else:
        books = Book.query()
        response.write(json.dumps(qsToJson(books)))

def deleteEntity(model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            e.key.delete()
    else:
        entities = model.query()
        for e in entities:
            e.key.delete()

# inspired by - http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property

def patchEntity(patch, model, id=None):
    if id:
        e = ndb.Key(model, int(id)).get()
        if e is not None:
            e_d = e.to_dict()
            patch_json = json.loads(patch)
            for key in e_d:
                if patch_json.get(key, None) is not None:
                    e_d[key] = patch_json[key]
            e.populate(**e_d)
            e.put()


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
            books = Book.query(Book.checkedIn == bool(is_checked_in))
            self.response.write(qsToJson(books))
        else:
            getEntity(self.response, Book, id)

    def post(self):
        book_json = json.loads(self.request.body)
        parent_key = ndb.Key(Book, "book_parent")
        book_id = Book.query().count()+1
        book_key = ndb.Key(Book, book_id)
        # switched required values to default values on failure?
        book = Book(title=book_json['title'],
                    isbn=book_json['isbn'],
                    genre=book_json['genre'],
                    author=book_json['author'],
                    checkedIn=book_json.get('checkedIn', True),
                    key=book_key)
        book.put()
        book_d = book.to_dict()
        book_d['id'] = book.key.id()
        self.response.write(json.dumps(book_d))

    def delete(self, id=None):
        deleteEntity(Book, id)

    def patch(self, id):
        patchEntity(self.request.body, Book, id)


class CustomerHandler(webapp2.RequestHandler):
    def get(self, id=None):
        getEntity(self.response, Customer, id)


    def post(self):
        customer_json = json.loads(self.request.body)
        customer_id = Customer.query().count()+1
        customer_key = ndb.Key(Customer, customer_id);
        customer = Customer(name=customer_json['name'],
                            balance=customer_json.get('balance', None),
                            checked_out=customer_json.get('checked_out', []),
                            key=customer_key)
        customer.put()
        c_d = customer.to_dict()
        c_d['id'] = customer.key.id()
        self.response.write(json.dumps(c_d))

    def delete(self, id):
        deleteEntity(Customer, id)

    def patch(self, id):
        patchEntity(self.request.body, Customer, id)

class CheckoutHandler(webapp2.RequestHandler):
    def put(self, customer_id, book_id):
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        customer.checked_out.append("/books/{}".format(book.key.id()))
        customer.put()
        book.checkedIn = False
        book.put()

    def delete(self, customer_id, book_id):
        customer = ndb.Key(Customer, int(customer_id)).get()
        book = ndb.Key(Book, int(book_id)).get()
        customer.checked_out.remove("/books/{}".format(book.key.id()))
        customer.put()


# http://stackoverflow.com/questions/26433719/google-appengine-api-yaml-errors-eventlisteneryamlerror-mapping-values-are-not
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    (r'/books', BookHandler),
    (r'/books/(\d+)', BookHandler),
    (r'/customers', CustomerHandler),
    (r'/customers/(\d+)', CustomerHandler),
    (r'/customers/(\d+)/books/(\d+)', CheckoutHandler)
], debug=True)
