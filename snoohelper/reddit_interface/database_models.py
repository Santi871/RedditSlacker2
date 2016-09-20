from peewee import IntegerField, TextField, SqliteDatabase, Model, BooleanField, TimestampField

db = SqliteDatabase('snoohelper_master.db', threadlocals=True, check_same_thread=False, timeout=30)


class BaseModel(Model):
    class Meta:
        database = db


class UserModel(BaseModel):
    username = TextField()
    removed_comments = IntegerField(default=0)
    removed_submissions = IntegerField(default=0)
    approved_comments = IntegerField(default=0)
    approved_submissions = IntegerField(default=0)
    bans = IntegerField(default=0)
    shadowbanned = BooleanField(default=False)
    tracked = BooleanField(default=False)
    warnings_muted = BooleanField(default=False)
    subreddit = TextField()


class SubmissionModel(BaseModel):
    submission_id = TextField()
    sticky_cmt_id = TextField(null=True)
    lock_type = TextField(null=True)
    lock_remaining = TimestampField(null=True)
    remove_remaining = TimestampField(null=True)
    subreddit = TextField()


class UnflairedSubmissionModel(BaseModel):
    submission_id = TextField()
    comment_id = TextField()
    subreddit = TextField()


class AlreadyDoneModel(BaseModel):
    thing_id = TextField(unique=True)
    timestamp = TimestampField()
    subreddit = TextField()