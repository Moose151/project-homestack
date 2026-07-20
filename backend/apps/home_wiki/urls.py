from django.urls import path

from apps.home_wiki.views import (
    CategoryDetailView,
    CategoryListView,
    PageDetailView,
    PageListView,
    WikiSearchView,
)

urlpatterns = [
    path("search/", WikiSearchView.as_view(), name="wiki-search"),

    path("categories/", CategoryListView.as_view(), name="wiki-category-list"),
    path("categories/<int:category_id>/", CategoryDetailView.as_view(), name="wiki-category-detail"),

    path("pages/", PageListView.as_view(), name="wiki-page-list"),
    path("pages/<int:page_id>/", PageDetailView.as_view(), name="wiki-page-detail"),
]
