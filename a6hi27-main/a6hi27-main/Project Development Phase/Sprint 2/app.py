from flask import Flask, render_template, request
import ibm_db
import json
import os
import pathlib
import requests
import tweepy
import google.auth.transport.requests
from flask_mail import Mail, Message
from random import randint
from flask import Flask, session, abort, redirect
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol

connectionstring="DATABASE=bludb;HOSTNAME=3883e7e4-18f5-4afe-be8c-fa31c41761d2.bs2io90l08kqb1od8lcg.databases.appdomain.cloud;PORT=31498;PROTOCOL=TCPIP;UID=kmy46098;PWD=PN0aG7meNBbB7HH1;SECURITY=SSL;"
connection = ibm_db.connect(connectionstring, '', '')

app = Flask(__name__)
app.debug = True


mail = Mail(app)
app.secret_key = "HireMe.com"

first_name = ""
last_name = ""
password = ""


app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = '2k19cse052@kiot.ac.in'
app.config['MAIL_PASSWORD'] = 'ibrwjgtyodyfzcvo'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

consumer_key = ''
consumer_secret = ''
tcallback = 'http://127.0.0.1:5000/tcallback'

GOOGLE_CLIENT_ID = ""
client_secrets_file = os.path.join(
    pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


@app.route("/signup")
@app.route("/")
def signup():
    return render_template("signup.html")


@app.route('/verification', methods=["POST", "GET"])
def verify():
    global first_name
    global last_name
    global password
    global otp

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        useremail = request.form.get('email')
        sql = "SELECT * FROM User WHERE email =?"
        stmt = ibm_db.prepare(connection, sql)
        ibm_db.bind_param(stmt, 1, useremail)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)

        if (account):
            return render_template('signup.html', msg="You are already a member, please login using your details")
        else:
            session['regmail'] = useremail
            otp = randint(000000, 999999)
            msg = Message(subject='OTP', sender='hackjacks@gmail.com',
                          recipients=[session['regmail']])
            msg.body = "You have succesfully registered for Hire Me!\nUse the OTP given below to verify your email ID.\n\t\t" + \
                str(otp)
            mail.send(msg)
            return render_template('verification.html')

    elif ("regmail" in session):
        if request.method == 'GET':
            otp = randint(000000, 999999)
            msg = Message(subject='OTP', sender='hackjacks@gmail.com',
                          recipients=[session['regmail']])
            msg.body = "You have succesfully registered for Hire Me!\nUse the OTP given below to verify your email ID.\n\t\t" + \
                str(otp)
            mail.send(msg)
            return render_template('verification.html', resendmsg="OTP has been resent")
    else:
        return redirect('/')


@app.route('/validate', methods=['POST', 'GET'])
def validate():
    if ('regmail' in session):
        global first_name
        global last_name
        global password
        user_otp = request.form['otp']
        if otp == int(user_otp):
            insert_sql = "INSERT INTO User(first_name,last_name,email,pass) VALUES (?,?,?,?)"
            prep_stmt = ibm_db.prepare(connection, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, first_name)
            ibm_db.bind_param(prep_stmt, 2, last_name)
            ibm_db.bind_param(prep_stmt, 3, session['regmail'])
            ibm_db.bind_param(prep_stmt, 4, password)
            ibm_db.execute(prep_stmt)
            return render_template('signin.html')
        else:
            return render_template('verification.html', msg="OTP is invalid. Please enter a valid OTP")
    else:
        return redirect('/')


@app.route("/googlelogin")
def googlelogin():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(
        session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["email_id"] = id_info.get("email")
    session["first_name"] = id_info.get("given_name")
    session["last_name"] = id_info.get("family_name")

    global first_name
    global last_name
    global useremail
    global password

    first_name = session['first_name']
    last_name = session['last_name']
    useremail = session['email_id']
    password = ""

    sql = "SELECT * FROM User WHERE email =?"
    stmt = ibm_db.prepare(connection, sql)
    ibm_db.bind_param(stmt, 1, useremail)
    ibm_db.execute(stmt)
    account = ibm_db.fetch_assoc(stmt)

    if account:
        if (account['NEWUSER'] == 1):
            return redirect('/profile')
        return redirect('/home')

    else:

        insert_sql = "INSERT INTO User(first_name,last_name,email,pass) VALUES (?,?,?,?)"
        prep_stmt = ibm_db.prepare(connection, insert_sql)
        ibm_db.bind_param(prep_stmt, 1, first_name)
        ibm_db.bind_param(prep_stmt, 2, last_name)
        ibm_db.bind_param(prep_stmt, 3, useremail)
        ibm_db.bind_param(prep_stmt, 4, password)
        ibm_db.execute(prep_stmt)
        return redirect("/profile")


@app.route('/tlogin')
def auth():
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, tcallback)
    url = auth.get_authorization_url()
    session['request_token'] = auth.request_token
    return redirect(url)


@app.route('/tcallback')
def twitter_callback():

    global first_name
    request_token = session['request_token']
    print(request_token)
    del session['request_token']

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, tcallback)
    auth.request_token = request_token
    verifier = request.args.get('oauth_verifier')
    auth.get_access_token(verifier)
    session['token'] = (auth.access_token, auth.access_token_secret)
    first_name = session['token']
    return redirect('/profile')


@app.route("/logout")
def logout():
    session.pop('useremail', None)
    session.pop('regmail', None)
    session.pop('newuser', None)
    session.pop('role', None)
    return redirect("/login")


@app.route("/home", methods=['GET', 'POST'])
def home():
    if "useremail" in session:
        if request.method == 'POST':
            user_search = request.form.get('search').replace(" ","").casefold()
            arr = []
            sql = "SELECT * FROM COMPANY"
            stmt = ibm_db.exec_immediate(connection, sql)
            dictionary = ibm_db.fetch_assoc(stmt)
            while dictionary != False:
                if dictionary['COMPANY_NAME'].replace(" ","").casefold() == user_search or dictionary['ROLE'].replace(" ","").casefold() == user_search or dictionary['SKILL_1'].replace(" ","").casefold() == user_search  or dictionary['SKILL_2'].replace(" ","").casefold() == user_search or dictionary['SKILL_3'].replace(" ","").casefold() == user_search:
                    dict = {
                        'jobid': dictionary['JOB_ID'], 'cname': dictionary['COMPANY_NAME'], 'role': dictionary['ROLE'], 'ex': dictionary['EXPERIENCE'], 'skill_1': dictionary['SKILL_1'], 'skill_2': dictionary['SKILL_2'], 'skill_3': dictionary['SKILL_3'], 'vacancy': dictionary['VACANCY'], 'stream': dictionary['STREAM'], 'job_location': dictionary['JOB_LOCATION'], 'salary': dictionary['SALARY'], 'link': dictionary['WEBSITE'], 'logo': dictionary['LOGO']
                    }
                    arr.append(dict)
                dictionary = ibm_db.fetch_assoc(stmt)
            companies = json.dumps(arr)
            return render_template("index.html", companies=companies, arr=arr)
        else:
            arr=[]
            sql = "SELECT * FROM COMPANY where skill_1 = ? or skill_2 = ? or skill_3 = ?"
            stmt = ibm_db.prepare(connection, sql)
            ibm_db.bind_param(stmt, 1, session['skill'])
            ibm_db.bind_param(stmt, 2, session['skill'])
            ibm_db.bind_param(stmt, 3, session['skill'])
            ibm_db.execute(stmt)
            dictionary = ibm_db.fetch_assoc(stmt)
            while dictionary != False:
                dict = {
                    'jobid': dictionary['JOB_ID'], 'cname': dictionary['COMPANY_NAME'], 'role': dictionary['ROLE'], 'ex': dictionary['EXPERIENCE'], 'skill_1': dictionary['SKILL_1'], 'skill_2': dictionary['SKILL_2'], 'skill_3': dictionary['SKILL_3'], 'vacancy': dictionary['VACANCY'], 'stream': dictionary['STREAM'], 'job_location': dictionary['JOB_LOCATION'], 'salary': dictionary['SALARY'], 'link': dictionary['WEBSITE'], 'logo': dictionary['LOGO']
                }
                arr.append(dict)
                dictionary = ibm_db.fetch_assoc(stmt)
            arr.reverse()
            companies = json.dumps(arr)
            return render_template("index.html", companies=companies, arr=arr)
    else:
        return redirect('/login')


@app.route('/like')
def store_like(request):
    session['jobid'] = request.POST.get('jobid')
    insert_sql = "INSERT INTO LIKES(USERID,JOBID) VALUES(?,?)"
    prep_stmt = ibm_db.prepare(connection, insert_sql)
    ibm_db.bind_param(prep_stmt, 1, session['userid'])
    ibm_db.bind_param(prep_stmt, 1, session['jobid'])
    ibm_db.execute(prep_stmt)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        useremail = request.form.get('email')
        password = request.form.get('password')
        sql = "SELECT * FROM user WHERE email =?"
        stmt = ibm_db.prepare(connection, sql)
        ibm_db.bind_param(stmt, 1, useremail)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        if account:
            session["useremail"] = useremail
            session["newuser"] = account['NEWUSER']
            if (password == str(account['PASS']).strip()):
                if (session['newuser'] == 1):
                    return redirect('/profile')
                else:
                    sql = "SELECT * FROM profile WHERE email_id =?"
                    stmt = ibm_db.prepare(connection, sql)
                    ibm_db.bind_param(stmt, 1, useremail)
                    ibm_db.execute(stmt)
                    account = ibm_db.fetch_assoc(stmt)
                    session['skill'] = account['SKILL']
                    return redirect('/home')
            else:
                return render_template('signin.html', msg="Password is invalid")
        else:
            return render_template('signin.html', msg="Email is invalid")
    else:
        if "useremail" in session:
            return redirect('/home')
        else:
            return render_template('signin.html')


@app.route("/profile", methods=["POST", "GET"])
def profile():
    if "useremail" in session:
        if (session['newuser'] == 1 and request.method == 'POST'):
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            mobile_no = request.form.get('mobile_no')
            address_line_1 = request.form.get('address_line_1')
            address_line_2 = request.form.get('address_line_2')
            zipcode = request.form.get('zipcode')
            city = request.form.get('city')
            education = request.form.get('education')
            country = request.form.get('countries')
            state = request.form.get('states')
            experience = request.form.get('experience')
            skill = request.form.get('skill')

            insert_sql = "INSERT INTO profile VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"

            prep_stmt = ibm_db.prepare(connection, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, first_name)
            ibm_db.bind_param(prep_stmt, 2, last_name)
            ibm_db.bind_param(prep_stmt, 3, mobile_no)
            ibm_db.bind_param(prep_stmt, 4, address_line_1)
            ibm_db.bind_param(prep_stmt, 5, address_line_2)
            ibm_db.bind_param(prep_stmt, 6, zipcode)
            ibm_db.bind_param(prep_stmt, 7, city)
            ibm_db.bind_param(prep_stmt, 8, session['useremail'])
            ibm_db.bind_param(prep_stmt, 9, education)
            ibm_db.bind_param(prep_stmt, 10, country)
            ibm_db.bind_param(prep_stmt, 11, state)
            ibm_db.bind_param(prep_stmt, 12, experience)
            ibm_db.bind_param(prep_stmt, 13, skill)
            ibm_db.execute(prep_stmt)

            insert_sql = "UPDATE USER SET newuser = false WHERE email=?"
            session['newuser'] = 0
            prep_stmt = ibm_db.prepare(connection, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, session['useremail'])
            ibm_db.execute(prep_stmt)
            session['skill'] = skill
            return redirect('/home')

        if (session['newuser'] == 0):
            sql = "SELECT * FROM profile WHERE email_id =?"
            stmt = ibm_db.prepare(connection, sql)
            ibm_db.bind_param(stmt, 1, session['useremail'])
            ibm_db.execute(stmt)
            account = ibm_db.fetch_assoc(stmt)
            first_name = account['FIRST_NAME']
            last_name = account['LAST_NAME']
            mobile_no = account['MOBILE_NUMBER']
            address_line_1 = account['ADDRESS_LINE_1']
            address_line_2 = account['ADDRESS_LINE_2']
            zipcode = account['ZIPCODE']
            education = account['EDUCATION']
            countries = account['COUNTRY']
            states = account['STATEE']
            city = account['CITY']
            experience = account['EXPERIENCE']
            skill = account['SKILL']
            return render_template('profile.html', email=session['useremail'], newuser=session['newuser'], first_name=first_name, last_name=last_name, address_line_1=address_line_1, address_line_2=address_line_2, zipcode=zipcode, education=education, countries=countries, states=states, experience=experience, mobile_no=mobile_no, city=city, skill=skill)

        else:
            return render_template('profile.html', newuser=session['newuser'], email=session['useremail'])
    else:
        return redirect("/login")


@app.route("/forgotpass", methods=["POST", "GET"])
def forgotpass():
    global i
    global otp
    global email

    if request.method == 'POST':

        useremail = request.form.get('email')
        user_otp = request.form.get('OTP')
        password = request.form.get('password')

        sql = "SELECT * FROM User WHERE email =?"
        stmt = ibm_db.prepare(connection, sql)
        ibm_db.bind_param(stmt, 1, useremail)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)

        if i == 1:
            if otp == int(user_otp):
                i = 2
                return render_template('forgotpass.html', i=i)
            else:
                return render_template('forgotpass.html', msg="OTP is invalid. Please enter a valid OTP", i=i)

        elif i == 2:
            sql = "UPDATE USER SET pass=? WHERE email=?"
            stmt = ibm_db.prepare(connection, sql)
            ibm_db.bind_param(stmt, 1, password)
            ibm_db.bind_param(stmt, 2, email)
            ibm_db.execute(stmt)
            i = 1
            return render_template('signin.html')

        elif i == 0:
            if (account):
                otp = randint(000000, 999999)
                email = request.form['email']
                msg = Message(subject='OTP', sender='hackjacks@gmail.com',
                              recipients=[email])
                msg.body = "Forgot your password?\n\nWe received a request to reset the password for your account.Use the OTP given below to reset the password.\n\n" + \
                    str(otp)
                mail.send(msg)
                i = 1
                return render_template('forgotpass.html', i=i)
            else:
                return render_template('forgotpass.html', msg="It looks like you are not yet our member!")
    i = 0
    return render_template('forgotpass.html')

@app.route("/adminlogin", methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        useremail = request.form.get('email')
        password = request.form.get('password')
        sql = "SELECT * FROM admin WHERE email =?"
        stmt = ibm_db.prepare(connection, sql)
        ibm_db.bind_param(stmt, 1, useremail)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        if account:
            session["useremail"] = useremail
            if (password == str(account['PASS']).strip()):
                return render_template('adminhome.html')
            else:
                return render_template('adminlogin.html', msg="Password is invalid")
        else:
            return render_template('adminlogin.html', msg="Email is invalid")
    else:
        return render_template('adminlogin.html')

@app.route("/adminhome", methods=['GET', 'POST'])
def adminhome():
    if "useremail" in session:
        if request.method == 'POST':
            company_name = request.form.get('company_name')
            role = request.form.get('role')
            skill_1 = request.form.get('skill_1')
            skill_2 = request.form.get('skill_2')
            skill_3 = request.form.get('skill_3')
            vacancy = request.form.get('vacancy')
            stream = request.form.get('stream')
            job_location = request.form.get('job_location')
            salary = request.form.get('salary')
            experience = request.form.get('experience')
            link = request.form.get('link')
            logo = request.form.get('logo')

            insert_sql = "INSERT INTO company (company_name, role, experience, skill_1, skill_2, skill_3, vacancy, stream, job_location, salary, website, logo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"

            prep_stmt = ibm_db.prepare(connection, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, company_name)
            ibm_db.bind_param(prep_stmt, 2, role)
            ibm_db.bind_param(prep_stmt, 3, experience)
            ibm_db.bind_param(prep_stmt, 4, skill_1)
            ibm_db.bind_param(prep_stmt, 5, skill_2)
            ibm_db.bind_param(prep_stmt, 6, skill_3)
            ibm_db.bind_param(prep_stmt, 7, vacancy)
            ibm_db.bind_param(prep_stmt, 8, stream)
            ibm_db.bind_param(prep_stmt, 9, job_location)
            ibm_db.bind_param(prep_stmt, 10, salary)
            ibm_db.bind_param(prep_stmt, 11, link)
            ibm_db.bind_param(prep_stmt, 12, logo)
            ibm_db.execute(prep_stmt)

            sql = 'SELECT email_id from profile Where skill = ? or skill = ? or skill = ?'
            stmt = ibm_db.prepare(connection, sql)
            ibm_db.bind_param(stmt, 1, skill_1)
            ibm_db.bind_param(stmt, 2, skill_2)
            ibm_db.bind_param(stmt, 3, skill_3)
            ibm_db.execute(stmt)
            account = ibm_db.fetch_assoc(stmt)
            while account != False:
                msg = Message(subject='OTP', sender='hackjacks@gmail.com',
                            recipients=[account['EMAIL_ID']])
                msg.body = company_name+" posted a new job"
                mail.send(msg)
                account = ibm_db.fetch_assoc(stmt)
            return render_template('adminhome.html')

        return render_template('adminhome.html')
    else:
        return render_template('adminlogin.html')
