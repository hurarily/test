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
    host="dpg-cnnh6qvjbltc738e7mpg-a",
    port="5432",
    user="database_7t6y_user",
    password="99PN2s0JjpJR5AUo7urO8SdYEftevRG8",
    database="database_7t6y")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (UID SERIAL PRIMARY KEY, account TEXT, password TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS data (account TEXT, _case TEXT, annotation TEXT, topic TEXT, proposal TEXT, imageurl TEXT)")

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
        image_url = None
        if request.method == 'POST':
            if 'design_case' in request.form:
                design_case = (request.form.get("design_case"))
                user_status[account]['case'] = str(design_case)
                temp = generate_annotations(design_case)
                if '2. Concept:' in temp:
                    appearance = temp.split('Appearance: ')[1].split('2. Concept:')[0]
                elif 'Concept:' in temp:
                    appearance = temp.split('Appearance: ')[1].split('Concept:')[0]
                if '3. Usage Scenarios:' in temp:
                    concept = temp.split('Concept: ')[1].split('3. Usage Scenarios:')[0]
                    if '4. Materials:' in temp:
                        usageScenarios = temp.split('3. Usage Scenarios: ')[1].split('4. Materials:')[0]
                    elif 'Materials:' in temp:
                        usageScenarios = temp.split('3. Usage Scenarios: ')[1].split('Materials:')[0]
                elif '3. Usage scenarios:' in temp:
                    concept = temp.split('Concept: ')[1].split('3. Usage scenarios:')[0]
                    if '4. Materials:' in temp:
                        usageScenarios = temp.split('3. Usage scenarios: ')[1].split('4. Materials:')[0]
                    elif 'Materials:' in temp:
                        usageScenarios = temp.split('3. Usage scenarios: ')[1].split('Materials:')[0]
                elif 'Usage Scenarios:' in temp:
                    concept = temp.split('Concept: ')[1].split('Usage Scenarios:')[0]
                    if '4. Materials:' in temp:
                        usageScenarios = temp.split('Usage Scenarios: ')[1].split('4. Materials:')[0]
                    elif 'Materials:' in temp:
                        usageScenarios = temp.split('Usage Scenarios: ')[1].split('Materials:')[0]
                elif 'Usage scenarios:' in temp:
                    concept = temp.split('Concept: ')[1].split('Usage scenarios:')[0]
                    if '4. Materials:' in temp:
                        usageScenarios = temp.split('Usage scenarios: ')[1].split('4. Materials:')[0]
                    elif 'Materials:' in temp:
                        usageScenarios = temp.split('Usage scenarios: ')[1].split('Materials:')[0]
                if '5. Functionality' in temp:
                    materials = temp.split('Materials: ')[1].split('5. Functionality:')[0]
                elif 'Functionality' in temp:
                    materials = temp.split('Materials: ')[1].split('Functionality:')[0]
                functionality = temp.split('Functionality: ')[1]
                user_status[account]['annotations_split'] = {'appearance': appearance, 'concept': concept, 'usageScenarios': usageScenarios, 'materials': materials, 'functionality': functionality}
                user_status[account]['annotations'] = temp
            elif 'design_topic' in request.form and user_status[account]['annotations'] is not None:
                design_topic = request.form.get("design_topic")
                user_status[account]['topic'] = design_topic
                user_status[account]['new_design_proposal'] = generate_design_proposal(design_topic, user_status[account]['annotations'])
            elif user_status[account]['new_design_proposal'] is not None:
                image_url = generate_image_from_text(user_status[account]['new_design_proposal'])
                cursor.execute(
                    'INSERT INTO data (account, _case, annotation, topic, proposal, imageurl) VALUES (%s, %s, %s, %s, %s, %s)', \
                        (account, user_status[account]['case'], user_status[account]['annotations'], user_status[account]['topic'], user_status[account]['new_design_proposal'], image_url))

        return render_template('index_a.html', session=user_status[account], account=account, image_url=image_url)


@app.route('/refresh/<account>', methods=['GET'])
def refresh(account):
    # 清除会话中的数据
    user_status[account]['case'] = None
    user_status[account]['annotations'] = None
    user_status[account]['topic'] = None
    user_status[account]['new_design_proposal'] = None
    user_status[account]['annotations_split'] = None
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
            if account not in user_status:
                user_status[account] = {'login': False, 'case': None, 'topic': None, 'annotations': None, 'new_design_proposal': None}
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
            user_status[temp[1]] = {'login': False, 'case': None, 'topic': None, 'annotations': None, 'new_design_proposal': None}

    if not successreg:
        r = {"text": 'fail', "msgacc": msgacc, "msgpwd": msgpwd, "msgpwd2": msgpwd2}
        return r
    else:
        return {"text": 'success'}
    

@app.route('/logout/<account>')
def logout(account):
    user_status[account]['login'] = False
    user_status[account]['case'] = None
    user_status[account]['annotations'] = None
    user_status[account]['new_design_proposal'] = None
    user_status[account]['annotations_split'] = None
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
            table += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href=%s>%s</td></tr>' % (row[1], row[2], row[3], row[4], row[5], row[5])
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