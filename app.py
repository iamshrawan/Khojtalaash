from flask import Flask, request, jsonify,redirect
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os
from flask import send_from_directory
from gensim.models import FastText
import warnings
warnings.filterwarnings("ignore")
import base64
import time


# from api import account_api
# from models import model_app
# from models import User, UserSchema, Item,ItemSchema

#init app here
app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir,'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["DEBUG"] = True
# app.register_blueprint(account_api)
# app.register_blueprint(model_app)


#Database
db = SQLAlchemy(app)
ma = Marshmallow(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column (db.String(80), nullable = False)
    password = db.Column (db.String(80), nullable = False)
    location = db.Column(db.String(80), nullable = False)
    phone = db.Column (db.String(15), nullable = False)
    def __init__(self, name, password, location):
        self.name = name
        self.password = password
        self.location = location
        self.phone = phone

class Item(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(80))
    location = db.Column (db.String(100), nullable =True)
    description = db.Column (db.String(100))
    catagory= db.Column (db.String(100))
    image = db.Column(db.String(100), nullable = True) 
    status = db.Column(db.String(100))
    user = db.Column (db.String(100), db.ForeignKey('user.id'),nullable = False)
    def __init__(self,name,location, description,catagory,image,status,user):
        self.name = name
        self.location = location
        self.description = description
        self.catagory = catagory
        self.image = image
        self.status = status
        self.user  =user

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id','name','password','location')

class ItemSchema(ma.Schema):
    class Meta:
        fields = ('id','name', 'catagory','location','description','catagory','image','status','user')



user_schema = UserSchema(strict = True)
users_schema = UserSchema(many = True, strict =True)

item_schema = ItemSchema(strict = True)
items_schema = ItemSchema (many =True, strict = True)

def get_similar_items(item, location):
    model = FastText.load("lf.model")
    if item in model.wv.vocab:
        similar = [(item,1.0)]
    else:    
        similar = model.most_similar(item, topn = 5)
        item = [item]
        model.build_vocab([item], update=True)
        model.train([item], total_examples=len([item]), epochs=model.epochs)

    print(similar)
    items = []
    for it, _ in similar:
        items.append(it)
    
    
    #print(model.wv.vocab)
    # if len(items) == 1:
    #    #result = db.engine.execute("SELECT name, location FROM Item WHERE name IN ('{0}')  AND catagory='found'".format(items[0], location))
    #    result = Item.query
    # else:
    #     result = db.engine.execute("SELECT name, location FROM Item WHERE name IN {0}  AND catagory='found'".format(items, location))
    results = []
    print(items)
    for item in items:
        result = Item.query.filter_by(name=item,catagory="found")
        result = items_schema.dump(result)
        if len(result.data)>0:
            results = results+result.data
    #result_data = [{column: value for column, value in row.items()} for row in result ]
    print(results)
    model.save('lf.model')
    try: 
        results = jsonify (results[0])
    except:
        results = jsonify({})
    return results


@app.route('/get_lost_items', methods = ['GET'])
def lost_items():
    lost_items = Item.query.all()
    result = items_schema.dump(lost_items)
    print(result.data)
    return jsonify(result.data)

@app.route('/get_found_items',methods = ['GET'])
def found_items():
    found_items = Item.query.filter_by(status= 1, catagory = 'found')
    result = items_schema.dump (found_items)
    return jsonify(result.data)

existing_item = None
@app.route ('/add_lost_item', methods = ['POST'])
def add_lost_items():
    #print(request.json)
    try:
        images = request.json['images']
        filename = 'pic'+str(time.time())+ '.jpg'
        with open(filename,'wb') as f:
            f.write(base64.b64decode(images))
        image_path = os.path.join ('images/'+ filename)
    except KeyError:
        print("No Image is Passed")
        image_path = os.path.join('images/'+filename)

    name = request.json['name']
    location = request.json['location']
    description = request.json['description']
    catagory = request.json['category']
    status = request.json ['status']
    user = request.json ['user']
    existing_item= get_similar_items(name,location)
    new_item = Item(name, location,description,catagory, filename, status, user)
    db.session.add(new_item)
    db.session.commit()
    return redirect("/notifications", code=302)


@app.route('/notifications', methods  = ['GET'])
def notification():
    if existing_item:
        return existing_item
    else:
        return jsonify({})

@app.route('/<path:filename>')
def sdir(filename):
    try:
        
        return send_from_directory(
            '',
            filename
        )
    except Exception as e:
        print (e)
        return ''



@app.route ('/add_found_item', methods = ['POST'])
def add_found_items():
    name = request.json['name']
    location = request.json['location']
    description = request.json['description']
    catagory = request.json['catagory']
    image = request.json['image']
    status = request.json ['status']
    user = request.json ['user']
    existing_item= get_similar_items(name,location)
    new_item = Item(name, location,description, catagory, image, status, user)
    db.session.add(new_item)
    db.session.commit()
    print(existing_item)
    return existing_item
    #return item_schema.jsonify(new_item)

@app.route('/lost_item_found/<id>', methods = ['PUT'])
def lost_item_found(id):
    item = Item.query.get (id)
    db.session.delete(item)

#server
if __name__=='__main__':
    app.run(host='0.0.0.0')