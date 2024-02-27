from flask import Flask, render_template, request, session, redirect, url_for
from openai import OpenAI
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# 实例化 OpenAI 客户端
client = OpenAI(api_key='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')

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root")
cursor = conn.cursor()
cursor.execute("DROP DATABASE db1")
cursor.execute("CREATE DATABASE IF NOT EXISTS db1")
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="db1")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS `users` (`UID` int(40) AUTO_INCREMENT, `account` VARCHAR(255), `password` VARCHAR(255), PRIMARY KEY (`UID`))")
cursor.execute("CREATE TABLE IF NOT EXISTS `data` (`UID` int(40), `case` VARCHAR(255), `annotation` LONGTEXT, `proposal` LONGTEXT, `imageurl` LONGTEXT)")

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/home', methods=['GET', 'POST'])
def index():
    print(session)
    if not session:
        return redirect(url_for('login'))
    else:
        if request.method == 'POST':
            if 'design_case' in request.form:
                design_case = (request.form.get("design_case"))
                session['case'] = str(design_case)
                session['annotations'] = generate_annotations(design_case)
                print(session['annotations'])
            elif 'design_topic' in request.form and 'annotations' in session:
                design_topic = request.form.get("design_topic")
                session['new_design_proposal'] = generate_design_proposal(design_topic, session['annotations'])
                print(session['new_design_proposal'])

        return render_template('index_a.html', session=session)


@app.route('/refresh', methods=['GET'])
def refresh():
    # 清除会话中的数据
    session.pop('case', None)
    session.pop('annotations', None)
    session.pop('new_design_proposal', None)
    return redirect(url_for('index'))


@app.route('/generate-image', methods=['GET', 'POST'])
def generate_image():
    if 'new_design_proposal' in session:
        design_proposal = session['new_design_proposal']
        image_url = generate_image_from_text(design_proposal)
        cursor.execute(
            'INSERT INTO `data` (`UID`, `case`, `annotation`, `proposal`, `imageurl`) VALUES (%s, %s, %s, %s, %s)', \
            (session['user']['id'], session['case'], session['annotations'], design_proposal, image_url))
        return render_template('image.html', image_url=image_url, session=session)
    return redirect(url_for('index'))


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
            session['user'] = {
                'id': user[0],
                'account': user[1],
            }
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

    if not successreg:
        r = {"text": 'fail', "msgacc": msgacc, "msgpwd": msgpwd, "msgpwd2": msgpwd2}
        return r
    else:
        return {"text": 'success'}
    

@app.route('/logout')
def logout():
    session.pop('case', None)
    session.pop('annotations', None)
    session.pop('new_design_proposal', None)
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/history')
def listhistory():
    if not session:
        return redirect(url_for('login'))
    else:
        cursor.execute('SELECT * FROM data WHERE UID = %s', (session['user']['id'], ))
        rows = cursor.fetchall()
        table = ''
        for row in rows:
            table += '<tr><td>%s</td><td>%s</td><td>%s</td><td><a href=%s>%s</td></tr>' % (row[1], row[2], row[3], row[4], row[4])
        return render_template('history.html', session=session, table=table)
    

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
    app.run(debug=True)
