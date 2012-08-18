from . import app, meetup, mongo
from flask import render_template, redirect, url_for, request, session, flash
from flask.ext.login import login_required, login_user, logout_user

from .forms import VenueClaimForm
from .logic import sync_user, get_unclaimed_venues
from .models import User, Venue


@app.route('/clear/')
def clear():
    session.clear()
    return redirect('/')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/have/')
def have():
    venues = get_unclaimed_venues()
    return render_template('have.html', venues=venues)


@app.route('/login/', methods=('GET', 'POST'))
def login():
    return meetup.authorize(callback=url_for('login_meetup_return'))


@app.route('/login/meetup/return/', methods=('GET',))
@meetup.authorized_handler
def login_meetup_return(oauth_response):
    session['meetup_token'] = (
        oauth_response['oauth_token'],
        oauth_response['oauth_token_secret']
    )
    session['member_id'] = oauth_response['member_id']
    return render_template('login.html')


@app.route('/login/sync/', methods=('GET',))
def login_sync():
    user = sync_user(session['member_id'])
    login_user(user, remember=True)
    return redirect(url_for('index'))


@app.route('/logout/')
def logout():
    session.pop('meetup_token', None)
    session.pop('meetup_member_id', None)
    logout_user()
    return redirect(url_for('.index'))


@app.route('/need/')
def need():
    return render_template('need.html')


@app.route('/venue/<int:_id>/claim/', methods=('GET', 'POST'))
def venue_claim(_id):
    venue = Venue(_id=_id)
    venue.load()

    user = User(_id=int(session['member_id']))
    user.load()

    # If the user has not email or phone number and the venue does, place
    # them on the user for the purpose for prepopulating the form.
    if not getattr(user, 'email', None) and getattr(venue, 'email', None):
        user.email = venue.email
    if not getattr(user, 'phone', None) and getattr(venue, 'phone', None):
        user.phone = venue.phone

    form = VenueClaimForm(request.form, obj=user)
    if request.method == 'POST' and form.validate():
        venue.claim(name=form.name.data, email=form.email.data,
            phone=form.phone.data)
        flash('Thank you for claiming %s' % venue.name, 'success')
        return redirect(url_for('index'))

    return render_template('venue/claim.html', venue=venue, form=form)


@meetup.tokengetter
def get_twitter_token():
    return session.get('meetup_token')
