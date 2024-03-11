from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
import os
# import mysql.connector
import psycopg2

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# 实例化 OpenAI 客户端
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="root")
# cursor = conn.cursor()
# cursor.execute("DROP DATABASE db1")
# cursor.execute("CREATE DATABASE IF NOT EXISTS db1")
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="root",
#     database="db1")
# cursor = conn.cursor()
conn = psycopg2.connect(
    host="dpg-cnnc82icn0vc738htolg-a",
    port="5432",
    user="database_o0qr_user",
    password="El0DJCn3tW0lXG6oBxJDEK1Mt68xtbu3",
    database="database_o0qr")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (UID SERIAL PRIMARY KEY, account TEXT, password TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS data (account TEXT, _case TEXT, annotation TEXT, proposal TEXT, imageurl TEXT)")

user_status = {}

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/home/<account>', methods=['GET', 'POST'])
def index(account):
    if request.form.get('account'):
        account = request.form.get('account')
    if user_status[account]['login'] == False:
        return redirect(url_for('login'))
    else:
        if request.method == 'POST':
            if 'design_case' in request.form:
                design_case = (request.form.get("design_case"))
                user_status[account]['case'] = str(design_case)
                user_status[account]['annotations'] = generate_annotations(design_case)
                print(user_status[account]['annotations'])
            elif 'design_topic' in request.form and user_status[account]['annotations'] is not None:
                design_topic = request.form.get("design_topic")
                user_status[account]['new_design_proposal'] = generate_design_proposal(design_topic, user_status[account]['annotations'])
                print(user_status[account]['new_design_proposal'])

        return render_template('index_a.html', session=user_status[account], account=account)


@app.route('/refresh/<account>', methods=['GET'])
def refresh(account):
    # 清除会话中的数据
    user_status[account]['case'] = None
    user_status[account]['annotations'] = None
    user_status[account]['new_design_proposal'] = None
    return redirect(url_for('index', account=account))


@app.route('/generate-image/<account>', methods=['GET', 'POST'])
def generate_image(account):
    if user_status[account]['new_design_proposal'] is not None:
        design_proposal = user_status[account]['new_design_proposal']
        image_url = generate_image_from_text(design_proposal)
        cursor.execute(
            'INSERT INTO data (account, _case, annotation, proposal, imageurl) VALUES (%s, %s, %s, %s, %s)', \
            (account, user_status[account]['case'], user_status[account]['annotations'], design_proposal, image_url))
        return render_template('image.html', image_url=image_url, session=user_status[account], account=account)
    return redirect(url_for('index', account=account))


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/login', methods=['POST'])
def logining():
    if 'account' in request.json and 'password' in request.json:
        account = request.json['account']
        password = request.json['password']
        cursor.execute(
            'SELECT * FROM users WHERE account = %s AND password = %s', (account, password))
        user = cursor.fetchone()

        if user:
            user_status[account]['login'] = True
            return 'success'
        else:
            return 'fail'
        

@app.route('/adduser', methods=['POST'])
def adduser():
    if 'account' in request.json and 'password' in request.json and 'password2' in request.json:
        account = request.json.get('account')
        password = request.json.get('password')
        password2 = request.json.get('password2')

        cursor.execute(
            'SELECT * FROM users WHERE account = %s', (account, ))
        exist = cursor.fetchone()
        msgacc, msgpwd, msgpwd2, successreg = '', '', '', ''
        if not account:
            msgacc = '*Required'
        elif exist:
            msgacc = '*Account has been registered'
        if not password:
            msgpwd = '*Required'
        if not password2:
            msgpwd2 = '*Required'
        elif password != password2:
            msgpwd2 = '*Password mismatch'
        if not msgacc and not msgpwd and not msgpwd2:
            cursor.execute(
                'INSERT INTO users (account, password) VALUES (%s, %s)', (account, password))
            conn.commit()
            successreg = 'success'
            cursor.execute('SELECT * FROM users WHERE account = %s', (account, ))
            temp = cursor.fetchone()
            user_status[temp[1]] = {'login': False, 'case': None, 'annotations': None, 'new_design_proposal': None}

    if not successreg:
        r = {"text": 'fail', "msgacc": msgacc, "msgpwd": msgpwd, "msgpwd2": msgpwd2}
        return r
    else:
        return {"text": 'success'}
    

@app.route('/logout/<account>')
def logout(account):
    cursor.execute('SELECT * FROM users WHERE account = %s', (account, ))
    temp = cursor.fetchone()
    user_status[temp[1]]['login'] = False
    return redirect(url_for('login'))


@app.route('/history/<account>')
def listhistory(account):
    if user_status[account]['login'] == False:
        return redirect(url_for('login'))
    else:
        cursor.execute('SELECT * FROM data WHERE account = %s', (account, ))
        rows = cursor.fetchall()
        table = ''
        for row in rows:
            table += '<tr><td>%s</td><td>%s</td><td>%s</td><td><a href=%s>%s</td></tr>' % (row[1], row[2], row[3], row[4], row[4])
        return render_template('history.html', session=user_status[account], table=table, account=account)
    

def generate_image_from_text(text):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=text,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        if response.data:
            return response.data[0].url
    except Exception as e:
        print("Error generating image:", e)
    return None


def generate_annotations(design_case):
    prompt = f"Based on the characteristics of the design case as described, write five unique design annotations through Bill Gaver's Annotated Portfolios, listing appearance, concept, usage scenarios, materials, and functionality. Ensure to include both abstract and concrete keywords.: {design_case}"
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=600,
        temperature=0.7
    )
    return response.choices[0].text.strip()


def generate_design_proposal(design_topic, annotations):
    prompt = f"You are a professional designer, known for your concise speech and complete sentences, focusing solely on describing the design object. Based on the following design annotations {annotations}, please conceive a new design proposal for {design_topic}. The object must fully comply with {design_topic}"
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=600,
        temperature=0.7
    )
    return response.choices[0].text.strip()


if __name__ == '__main__':
    app.run(debug=True, port=5432)