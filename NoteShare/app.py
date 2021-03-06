import os
from flask import (
    Flask,
    flash,
    request,
    redirect,
    url_for,
    render_template,
    jsonify,
    send_from_directory,
    abort,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, StringField, SubmitField
from flask_uploads import (
    UploadSet,
    configure_uploads,
    IMAGES,
    TEXT,
    DOCUMENTS,
    ARCHIVES,
    UploadNotAllowed,
)
from flask_bootstrap import Bootstrap

app = Flask(__name__)
folders = UploadSet(
    "folders",
    ("pdf",) + TEXT + IMAGES + ARCHIVES + DOCUMENTS,
    default_dest=lambda x: "storage/misc",
)
app.config["UPLOAD_FOLDER"] = "./"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # maximum size of the file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db/finaldb.sqlite"
app.config["SECRET_KEY"] = "secret"
Bootstrap(app)
configure_uploads(app, folders)
db = SQLAlchemy(app)


class Courses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sem_name = db.Column(db.String(80))  # Monsoon19
    course_name = db.Column(db.String(80))  # Data Str and Algo


class CourseForm(FlaskForm):
    sem = SelectField(
        "Year",
        choices=[
            (sem[0], sem[0])
            for sem in sorted(
                set(Courses.query.with_entities(Courses.sem_name)), reverse=True
            )
        ],
    )
    course = SelectField(
        "Course",
        choices=[
            (course[0], course[0])
            for course in set(Courses.query.with_entities(Courses.course_name))
        ],
    )
    upload_file = FileField(
        "File",
        validators=[
            FileRequired("Please choose a file."),
            FileAllowed(folders, "Please select a valid file."),
        ],
    )
    submit_form = SubmitField("Upload")


class SearchForm(FlaskForm):
    sem = SelectField(
        "Semester",
        choices=[("Any", "Any")]
        + [
            (sem[0], sem[0])
            for sem in sorted(
                set(Courses.query.with_entities(Courses.sem_name)), reverse=True
            )
        ],
    )
    course = SelectField(
        "Course",
        choices=[("Any", "Any")]
        + [
            (course[0], course[0])
            for course in set(Courses.query.with_entities(Courses.course_name))
        ],
    )
    search_query = StringField()
    submit_query = SubmitField("Submit")


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.getcwd(), "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )


@app.route("/browse", methods=["GET", "POST"])
def browse():
    search_form = SearchForm()
    sem = "Any"
    course = "Any"
    search_query = ""
    if search_form.validate_on_submit():
        sem = search_form.sem.data
        course = search_form.course.data
        search_query = search_form.search_query.data.lower()

    file_list = []
    file_path = os.getcwd() + "/storage/"
    filedirs = os.listdir(file_path)  # access all semester dirs
    dirs = []  # list of [sem,course] pairs

    if sem != "Any":
        courses_in_sem = os.listdir(file_path + "/" + sem)
        if course == "Any":
            for each_course in courses_in_sem:
                dirs.append([sem, each_course])
        elif course in courses_in_sem:
            dirs.append([sem, course])
    else:
        for each_sem in filedirs:  # access course dirs for all sem
            courses_in_sem = os.listdir(file_path + "/" + each_sem)
            if course == "Any":
                for each_course in courses_in_sem:
                    dirs.append([each_sem, each_course])
            elif course in courses_in_sem:
                dirs.append([each_sem, course])

    counter = 1
    for each_dir in dirs:
        all_files = os.listdir(
            file_path + "/" + each_dir[0] + "/" + each_dir[1]
        )  # list of files in second tier dir
        relative_course_path = each_dir[0] + "/" + each_dir[1]
        for each_file in all_files:
            file_list.append(
                (
                    each_dir[0],
                    each_dir[1],
                    (url_for("browse") + "/" + relative_course_path + "/" + each_file),
                    each_file,
                    counter,
                )
            )
            counter += 1

    if search_query != "":
        modified = []
        for entry in file_list:
            if search_query in entry[3].lower():
                modified.append(entry)
        file_list = modified

    selected_form = (sem, course, search_query)

    return render_template(
        "browse.html",
        selections=selected_form,
        filelist=file_list,
        search_form=search_form,
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    form = CourseForm()
    if form.validate_on_submit():
        # customise file path in local directory according to the data entered
        file_path = "../" + str(form.sem.data) + "/" + str(form.course.data)
        # store the file
        try:
            folders.save(form.upload_file.data, folder=file_path)
        except UploadNotAllowed:
            flash("Unsuccesful, please retry.")

        flash('Saved "' + str(form.upload_file.data.filename) + '"')

    return render_template("upload.html", form=form)


@app.route("/browse/<sem>/<course>/<filename>", methods=["GET", "POST"])
def filedisp(sem, course, filename):
    try:
        path_extention = "/storage/" + sem + "/" + course
        file_path = os.getcwd() + path_extention
        return send_from_directory(file_path, filename)
    except FileNotFoundError:
        abort(404)


@app.route("/course/<sem>")
def course(sem):
    course_list = []

    if sem != "Any":
        courses = Courses.query.filter_by(sem_name=sem).all()
    else:
        courses = Courses.query.with_entities(Courses.course_name)

    for course in courses:
        course_list.append({"name": course.course_name})

    return jsonify({"courses": course_list})


if __name__ == "__main__":
    app.run(debug=True)
