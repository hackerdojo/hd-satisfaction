#!/usr/bin/env python

import hashlib, random
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from django.utils import simplejson
from google.appengine.api import users
from datetime import datetime

METRICS = ["Overall","Cleanliness","Value","Community"]
GRADES = {'A':100.0,'B':90.0,'C':80.0,'D':70.0,'F':60.0}
REVSERSE_GRADES = dict((v,k) for k, v in GRADES.iteritems())

class SatisfactionMetric(db.Model):
  metric     = db.StringProperty()
  grade      = db.FloatProperty()
  who        = db.UserProperty()
  when       = db.DateTimeProperty(auto_now=True)


class MainHandler(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url('/'))
    else:
      survey = []
      for metric in METRICS:
        survey_item = {}
        survey_item['metric'] = metric
        survey_item['grade'] = None
        existing_metric = None
        existing_metric_all_months = SatisfactionMetric.all().filter('who =', user).filter('metric =', metric).fetch(500)
        for m in existing_metric_all_months:
          if m.when.month == datetime.now().month and m.when.year == datetime.now().year:
            existing_metric = m
        if existing_metric:
          survey_item['grade'] = REVSERSE_GRADES[existing_metric.grade]
        survey.append(survey_item)
      grades = sorted(GRADES.keys())
      self.response.out.write(template.render('templates/main.html', locals()))      

  def post(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url('/'))
    else:
      for metric in METRICS:
        try:
          grade = GRADES[self.request.get(metric)]
          sm = None
          existing_metric_all_months = SatisfactionMetric.all().filter('who =', user).filter('metric =', metric).fetch(500)
          for m in existing_metric_all_months:
            if m.when.month == datetime.now().month and m.when.year == datetime.now().year:
              sm = m
          if not sm:
            sm = SatisfactionMetric(metric=metric,who=user)
          sm.grade = grade
          sm.put()        
        except KeyError, e:
          existing_metric_all_months = SatisfactionMetric.all().filter('who =', user).filter('metric =', metric).fetch(500)
          for m in existing_metric_all_months:
            if m.when.month == datetime.now().month and m.when.year == datetime.now().year:
              m.delete()
      self.response.out.write(template.render('templates/thanks.html', locals()))      

# Sample Output:
#
#  [
#     {
#        "grade":90.0,
#        "metric":"General",
#        "who":"96f81e4886",
#        "exact_time":"01-20-2012 00:56:30",
#        "month":"2012-01"
#     },
   
class AllDataHandler(webapp.RequestHandler):
  def get(self):
    seed = str(random.random())
    
    def to_dict(data):
        m = hashlib.md5()
        m.update(data.who.email())
        m.update(seed)
        
        return dict(
            metric=data.metric,
            grade=data.grade,
            who=m.hexdigest()[0:10],
            month=data.when.strftime("%Y-%m"),
            exact_time=data.when.strftime("%m-%d-%Y %H:%M:%S"),)
            
    self.response.out.write(simplejson.dumps([to_dict(data) for data in SatisfactionMetric.all()]))

# How many people answered each month
#
# Sample:
#
# {"2012-01": 12}

class BasicDataHandler(webapp.RequestHandler):
  def get(self):
    
    monthly_count = {}
    monthly_users = {}
    
    for sm in SatisfactionMetric.all():
        month = sm.when.strftime("%Y-%m")
        user = sm.who.email()
        if month in monthly_count:
            if user not in monthly_users[month]:
              monthly_count[month] += 1
            monthly_users[month][user] = 1
        else:
            monthly_count[month] = 0
            monthly_users[month] = {}
                    
    self.response.out.write(simplejson.dumps(monthly_count))


def main():
    application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/api/all', AllDataHandler),
      ('/api/basic', BasicDataHandler),
    ],debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
