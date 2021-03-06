from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponse, Http404, JsonResponse
from leave_application.forms import (FacultyLeaveForm,
                                     StaffLeaveForm,
                                     StudentLeaveForm,)

from user_app.models import Administration, Replacement, ExtraInfo
from leave_application.models import (Leave, CurrentLeaveRequest,
                                      LeaveRequest, LeavesCount,
                                      LeaveMigration,)
from django.contrib.auth.models import User
from leave_application.helpers import FormData, get_object_or_none


class ApplyLeave(View):
    """
        A Class Based View which handles user applying for leave
    """
    def get(self, request):
        """
            view to handle get request to /leave/apply
        """
        # TODO: Check if leave not rejected or accepted and leave instance belongs to user
        # TODO: Take another value as action so that action can specify edit or delete with same constraint

        # id = request.GET.get('id')
        # if id:
        #     leave = get_object_or_404(Leave, id=id)
        #     user_type = self.get_user_type(request)
        #     if user_type == 'faculty':
        #         form = FacultyLeaveForm(leave, user=request.user)
        #     elif user_type == 'staff':
        #         form = StaffLeaveForm(leave, user=request.user)
        #     else:
        #         form = StudentLeaveForm(leave)
        #     return render(request, 'leave_application/apply_for_leave.html', {'form': form, 'title': 'Leave', 'action':'Edit'})
        form = self.get_form(request)
        return render(request, 'leave_application/apply_for_leave.html', {'form': form, 'title': 'Leave', 'action':'Apply'})

    def post(self, request):
        """
            view to handle post request to /leave/apply
        """
        form = self.get_form(request)

        if form.is_valid():
            type_of_leave = form.cleaned_data.get('type_of_leave', 'casual')
            acad_done = False if form.cleaned_data.get('acad_rep', False) else True
            admin_done = False if form.cleaned_data.get('admin_rep', False) else True
            academic_replacement = get_object_or_none(User, username=form.cleaned_data.get('acad_rep'))
            administrative_replacement = get_object_or_none(User,
                                                            username=form.cleaned_data.get('admin_rep'))
            try:
                leave_obj = Leave.objects.create(
                    applicant = request.user,
                    type_of_leave = type_of_leave,
                    academic_replacement = academic_replacement,
                    administrative_replacement = administrative_replacement,
                    purpose = form.cleaned_data['purpose'],
                    acad_done = acad_done,
                    admin_done = admin_done,
                    leave_address = form.cleaned_data.get('leave_address', ''),
                    start_date = form.cleaned_data['start_date'],
                    end_date = form.cleaned_data['end_date'],
                )

            except Exception as e:
                print(e)
                return render(request,
                              'leave_application/apply_for_leave.html',
                              {'form': form, 'message': 'Failed'})
            return render(request, 'leave_application/apply_for_leave.html', {'message': 'success', 'title': 'Leave', 'action':'Apply'})

        else:
            return render(request, 'leave_application/apply_for_leave.html', {'form': form, 'title': 'Leave', 'action':'Apply'})

    # def delete(self, request):
    #     id = request.DELETE.get('id', None)
    #
    #     leave = get_object_or_none(Leave, id=id)
    #     today = datetime.date.today()
    #     if not id or not leave or leave.applicant != request.user or leave.start_date < today:
    #         return JsonResponse({'message': 'Deletion Faild', 'type': 'error'}, status=200)
    #
    #     leave.delete()
    #     return JsonResponse({'message': 'Successfully Deleted', 'type': 'success'}, status=200)

    def get_user_type(self, request):
        return request.user.extrainfo.user_type

    def get_form(self, request):

        user_type = self.get_user_type(request)

        if user_type == 'faculty':
            form = self.get_form_object(FacultyLeaveForm, request)
        elif user_type == 'staff':
            form = self.get_form_object(StaffLeaveForm, request)
        else:
            form = self.get_form_object(StudentLeaveForm, request)

        return form

    def get_form_object(self, cls, request):

        if request.method == 'GET':
            return cls(initial={}, user=request.user)
        else:
            return cls(request.POST, user=request.user)


class ProcessRequest(View):

    def get(self, request, id):

        leave_request = get_object_or_404(CurrentLeaveRequest, id=id)
        type_of_leave = leave_request.leave.type_of_leave

        do = request.GET.get('do')
        remark = request.GET.get('remark', '')

        sanc_auth = leave_request.applicant.extrainfo.sanctioning_authority
        sanc_officer = leave_request.applicant.extrainfo.sanctioning_officer

        if leave_request.requested_from in list(rep.replacee for rep in request.user.replacing.all()):
            designation = leave_request.position
        else:
            designation = request.user.extrainfo.designation

        for_replacement = leave_request.permission == 'academic' \
                    or leave_request.permission == 'admin'

        if do == 'accept':

            if leave_request.applicant.extrainfo.user_type == 'student' \
                and request.user == leave_request.requested_from:
                return self.process_student_request(sanc_auth, leave_request, remark, True)

            if leave_request.permission == 'academic':
                if leave_request.leave.academic_replacement == request.user:
                    leave_request = self.create_leave_request(leave_request, False, accept=True, remark=remark)
                    leave_request.leave.acad_done = True
                else:
                    return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

            elif leave_request.permission == 'admin':
                if leave_request.leave.administrative_replacement == request.user:
                    leave_request = self.create_leave_request(leave_request, False, accept=True, remark=remark)
                    leave_request.leave.admin_done = True
                else:
                    return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

            elif leave_request.permission == 'sanc_auth':

                # requested_from =

                if sanc_auth == designation and type_of_leave in ['casual', 'restricted']:

                    leave_request = self.create_leave_request(leave_request, True, accept=True, remark=remark)
                    leave_request.leave.status = 'accepted'
                    leave_request.leave.save()

                else:
                    return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

            elif leave_request.permission == 'sanc_officer':

                if sanc_officer == designation:

                    leave_request = self.create_leave_request(leave_request, True, accept=True, remark=remark)
                    leave_request.leave.status = 'accepted'
                    leave_request.leave.save()

                else:
                    return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

            else:
                return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

            leave_request.leave.save()
            if for_replacement and leave_request.leave.acad_done \
               and leave_request.leave.admin_done:
                print(sanc_auth.name)
                next_user = ExtraInfo.objects.get(designation=sanc_auth).user
                CurrentLeaveRequest.objects.create(
                    applicant = leave_request.applicant,
                    requested_from = next_user,
                    position = sanc_auth,
                    leave = leave_request.leave,
                    permission = 'sanc_auth',
                )

        elif do == 'reject':
            if leave_request.applicant.extrainfo.user_type == 'student' \
               and request.user == leave_request.requested_from:
                return self.process_student_request(sanc_auth, leave_request, remark, False)

            if sanc_auth == designation and type_of_leave not in ['casual', 'restricted']:
                raise Http404

            if sanc_auth == sanc_officer and designation == sanc_auth:
                self.create_leave_request(leave_request, True, accept=False, remark=remark)

            elif designation in [sanc_auth, sanc_officer]:
                leave_request = self.create_leave_request(leave_request,
                                                          True, accept=False,
                                                          remark=remark)
            elif leave_request.requested_from == request.user:
                leaves_data = leave_request.leave.cur_requests
                for leave in leaves_data:
                    self.create_leave_request(leave, False, accept=False, remark=remark)

            else:
                return JsonResponse({'message':'Not Allowed', 'type': 'error'}, status=200)

            leave_request.leave.status = 'rejected'
            leave_request.leave.save()

        elif do == 'forward':

            if leave_request.applicant.extrainfo.user_type == 'student':
                raise Http404

            if sanc_auth == designation and type_of_leave not in ['casual', 'restricted']:
                leave_request = self.create_leave_request(leave_request, False, accept=True, remark=remark)
                sanc_officer_user = Administration.objects.filter(position=sanc_officer).first().administrator
                CurrentLeaveRequest.objects.create(
                    applicant=leave_request.applicant,
                    requested_from = sanc_officer_user,
                    position = sanc_officer,
                    leave = leave_request.leave,
                    permission = 'sanc_officer',
                )

            else:
                return JsonResponse({'message': 'Not allowed', 'type': 'error'}, status=200)

        else:
            raise Http404

        return JsonResponse({'message': 'Operation Successful'}, status=200)

    def create_leave_request(self, cur_leave_request, final, accept=False, remark=''):
        leave_request = LeaveRequest.objects.create(
            leave = cur_leave_request.leave,
            applicant = cur_leave_request.applicant,
            requested_from = cur_leave_request.requested_from,
            remark = remark,
            position = cur_leave_request.position,
            status = accept,
        )

        if not accept and final:
            cur_leave_request.leave.status = 'rejected'
        elif final:

            count = LeavesCount.objects.get(user=cur_leave_request.applicant)

            remain = getattr(count, cur_leave_request.leave.type_of_leave)
            required_leaves = cur_leave_request.leave.count_work_days

            if remain < required_leaves:
                cur_leave_request.leave.status = 'outdated'
            else:
                setattr(count, cur_leave_request.leave.type_of_leave,
                               remain - required_leaves)
                count.save()
                self.create_migration(cur_leave_request.leave)
                cur_leave_request.leave.status = 'accepted'

        cur_leave_request.delete()
        return leave_request

    def process_student_request(self, sanc_auth, leave_request, remark, process):

        outcome = 'accepted' if process else 'rejected'
        new_leave_request = LeaveRequest.objects.create(
            applicant = leave_request.applicant,
            requested_from = leave_request.requested_from,
            position = leave_request.position,
            leave = leave_request.leave,
            status = process,
            remark = remark,
        )
        new_leave_request.leave.status = outcome
        new_leave_request.leave.save()
        leave_request.delete()
        return JsonResponse({'message': 'Successful', 'type': 'success'}, status=200)

    def create_migration(self, leave):
        import datetime

        if leave.start_date <= datetime.date.today():
            Replacement.objects.create(
                replacee = leave.applicant,
                replacer = leave.academic_replacement,
                replacement_type = 'academic',
            )
            Replacement.objects.create(
                replacee = leave.applicant,
                replacer = leave.administrative_replacement,
                replacement_type = 'administrative',
            )

        else:
            # if leave.start_date not in to_be.migrations.keys():
                # to_be.migrations[leave.start_date] = []

            LeaveMigration.objects.create(
                type = 'add',
                replacee = leave.applicant,
                replacer = leave.academic_replacement,
                start_date = leave.start_date,
                end_date = leave.end_date,
                replacement_type = 'academic',
            )

            LeaveMigration.objects.create(
                type = 'add',
                replacee = leave.applicant,
                replacer = leave.administrative_replacement,
                start_date = leave.start_date,
                end_date = leave.end_date,
                replacement_type = 'administrative',
            )

    def is_problematic(self, leave):
        #TODO: Add automatic hadling of outdated or problematic leave requests
        pass

class GetApplications(View):

    def get(self, request):

        prequest_list = LeaveRequest.objects.filter(requested_from=request.user).order_by('-id')

        request_list = list(map(lambda x: self.should_forward(request, x),
                           CurrentLeaveRequest.objects.filter(requested_from=request.user).order_by('-id')))

        for reps in Replacement.objects.filter(replacer=request.user, replacement_type='administrative'):

            request_list += list(map(lambda x: self.should_forward(request, x),
                               CurrentLeaveRequest.objects.filter(requested_from=reps.replacee)))


        count = len(request_list)
        return render(request, 'leave_application/get_requests.html', {'requests': request_list,
                                                                       'title':'Leave',
                                                                       'action':'ViewRequests',
                                                                       'count':count,
                                                                       'prequests':prequest_list})

    def should_forward(self, request, query_obj):

        obj = FormData(request, query_obj)
        sanc_auth = query_obj.applicant.extrainfo.sanctioning_authority
        sanc_officer = query_obj.applicant.extrainfo.sanctioning_officer
        type_of_leave = query_obj.leave.type_of_leave

        designation = request.user.extrainfo.designation

        if (sanc_auth == designation and type_of_leave not in ['casual', 'restricted']) \
             and query_obj.permission not in ['academic', 'admin']:

             obj.forward = True

        else:
            obj.forward = False
        print(obj)
        return obj

class GetLeaves(View):

    def get(self, request):

        leave_list = Leave.objects.filter(applicant=request.user).order_by('-id')
        count = len(list(leave_list))
        return render(request, 'leave_application/get_leaves.html', {'leaves':leave_list,
                                                                     'count':count,
                                                                     'title':'Leave',
                                                                     'action':'ViewLeaves'})



"""

$.ajax({
    type: 'delete',
    url: '/leave/apply',
    data: {'id': 17},
    success: function(data){
        alert(data.message);
    },
    error: function(err){
        alert('error');
    }
});

"""
