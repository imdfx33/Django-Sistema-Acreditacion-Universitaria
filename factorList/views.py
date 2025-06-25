# factorList/views.py
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from factorManager.models import Factor
from django.contrib import messages
from django.db.models import Prefetch
from aspectManager.models import Aspect
from django.db.models import Count, Q
from factorManager.models import Project
from projects.models import Project

class FactorListView(LoginRequiredMixin, ListView):
    model               = Factor
    template_name       = 'factorList/factor_list.html'
    context_object_name = 'factors'
    paginate_by         = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('project')
        q         = self.request.GET.get('q')
        proyecto  = self.request.GET.get('proyecto')
        estado    = self.request.GET.get('estado')
        start     = self.request.GET.get('start_date')
        end       = self.request.GET.get('end_date')

        if q:
            qs = qs.filter(name__icontains=q)
        if proyecto:
            qs = qs.filter(project__id=proyecto)
        if estado:
            qs = qs.filter(status=estado)
        if start:
            qs = qs.filter(start_date__gte=start)
        if end:
            qs = qs.filter(end_date__lte=end)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['proyectos']     = Project.objects.all()
        # asumimos que tu modelo Factor define STATUS_CHOICES
        ctx['estado_choices'] = Factor._meta.get_field('status').choices
        return ctx

@login_required(login_url='login') # @ para proteger la vista
def factor_detail(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    # Anotamos cada trait con total_aspects y approved_aspects
    traits = factor.traits.annotate(
        total_aspects=Count('aspects', distinct=True),
        approved_aspects=Count('aspects', filter=Q(aspects__approved=True), distinct=True),
    )

    context = {
        'factor': factor,
        'traits': traits,
        'project': factor.project,
    }
    return render(request, 'factorList/factor_detail.html', context)

# ------------- Acciones de estado -------------
@login_required(login_url='login')
def approve_factor(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    # Usamos la propiedad approved_percentage del modelo
    if factor.approved_percentage < 100:
        messages.error(
            request,
            "No puedes aprobar un factor cuyo progreso sea menor al 100 %."
        )
    else:
        factor.status = 'approved'
        factor.save()
        messages.success(request, f"Factor «{factor.name}» aprobado.")
    return redirect('factor_detail', pk=pk)


@login_required(login_url='login')
def reject_factor(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    factor.status = 'rejected'
    factor.save()
    messages.success(request, f"Factor «{ factor.name }» rechazado.")
    return redirect('factor_detail', pk=pk)