from flask import Flask, render_template, request, session, url_for, redirect
import hashlib
import pymysql.cursors
from datetime import datetime
SALT = 'sevenoriginal'
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port=3306,
                       user='root',
                       password='root',
                       db='finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def hello():
    return render_template('index.html') 

@app.route('/login')
def login():
    return render_template('login.html')
    
@app.route('/register')
def register():
    return render_template('register.html')
    
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed_password))
    
    data = cursor.fetchone()
    
    cursor.close()
    if(data):
        session['username'] = username
        return redirect(url_for('home'))
    else:
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    firstName = request.form['fName']
    lastName = request.form['lName']
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    email = request.form['email']
    cursor = conn.cursor()
    
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    
    data = cursor.fetchone()
    
    if(data):
        error = "This user already exists"
        cursor.close()
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, hashed_password, firstName, lastName, email))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home')
def home():
    user = session['username']
    return render_template('home.html', username=user)

@app.route('/postPhoto')
def postPhoto():
    username = session['username']
    
    return render_template('postPhoto.html')

@app.route('/postPhotoAuth', methods=['GET','POST'])
def postPhotoAuth():
    #get data about photo
    poster = session['username']
    postingDateTime = datetime.now()
    filePath = request.form['filePath']
    visibleToAll = request.form.get('allFollowers') != None
    caption = request.form['caption']
    
    cursor = conn.cursor()
    ins = 'INSERT INTO photo(postingDate, filePath, allFollowers, caption, poster) VALUES(%s, %s, %s, %s, %s)'
    
    if visibleToAll:
        cursor.execute(ins, (postingDateTime, filePath, 1, caption, poster))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    else:
        cursor.execute(ins, (postingDateTime, filePath, 0, caption, poster))
        conn.commit()
        pID = cursor.lastrowid
        
        query = 'SELECT groupName, groupCreator FROM belongto WHERE username=%s'
        cursor.execute(query, (poster))
        data = cursor.fetchall()
        for line in data:
            print(line)
        cursor.close()
        return render_template('chooseGroups.html', group_list=data, pID=pID)

@app.route('/chooseGroups', methods=['GET','POST'])
def chooseGroups():
    poster = session['username']
    cursor = conn.cursor()
    #get pID from url parameters
    pID = request.args['pID']
    ins = "INSERT INTO sharedWith VALUES(%s, %s, %s)"
    for groupName in request.form.keys():
        #User could belong to 2+ groups with the same name but diff creators
        creatorList = request.form.getlist(groupName)
        for creator in creatorList:
            cursor.execute(ins, (pID, groupName, creator))
        conn.commit()
    return render_template('home.html', username=poster)
    
@app.route('/makeFriendGroup')
def makeFriendGroup():
    username = session['username']
    cursor = conn.cursor()
    query = 'SELECT follower FROM follow WHERE followee = %s'
    cursor.execute(query, username)
    data = cursor.fetchall()
    return render_template('makeFriendGroup.html', friend_list = data)
    
@app.route('/makeFriendGroupAuth', methods=['GET','POST'])
def makeFriendGroupAuth():
    creator = session['username']
    groupName = request.form['groupName']
    description = request.form.get('description')
    
    cursor = conn.cursor()
    query = 'SELECT * FROM friendgroup WHERE groupName = %s AND groupCreator = %s'
    cursor.execute(query, (groupName, creator))
    data = cursor.fetchone()
    error = None
    if(data):
        error = 'You already have a group named ' + groupName
        cursor.close()
        return render_template('makeFriendGroup.html', error=error)
    else:
        ins = 'INSERT INTO friendgroup VALUES(%s, %s, %s)'
        cursor.execute(ins, (groupName, creator, description))
        conn.commit()
        ins = 'INSERT INTO belongTo VALUES(%s, %s, %s)'
        cursor.execute(ins, (creator, groupName, creator))
        conn.commit()
        friendsToBeAdded = request.form.getlist('follower')
        print(friendsToBeAdded)
        for friend in friendsToBeAdded:
            print(friend)
            cursor.execute(ins, (friend, groupName, creator))
            conn.commit()
        cursor.close()
        return render_template('home.html', username=creator)

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
    
app.secret_key = 'hopcrunch'

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)