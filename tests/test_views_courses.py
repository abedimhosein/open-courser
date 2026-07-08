"""Tests for course views: toggle, complete, reset, progress."""

from django.test import TestCase, Client
from django.urls import reverse

from apps.courses.models import Course, CourseNode, Tag
from apps.media.models import MediaMetadata
from apps.progress.models import WatchHistory
from apps.workspaces.models import Workspace


class CourseViewTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(name="Test Workspace")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Test Course",
            root_path="/tmp/test",
        )
        self.video_node = CourseNode.objects.create(
            course=self.course,
            name="video.mp4",
            relative_path="video.mp4",
            node_type="file",
            file_type="video",
        )
        self.meta = MediaMetadata.objects.create(
            course_node=self.video_node,
            duration=300.0,
        )


class TestCourseToggleLock(CourseViewTestBase):
    def test_toggles_lock(self):
        self.assertFalse(self.course.locked)
        response = self.client.post(
            reverse("course_toggle_lock", args=[self.course.pk])
        )
        self.course.refresh_from_db()
        self.assertTrue(self.course.locked)

    def test_toggles_unlock(self):
        self.course.locked = True
        self.course.save()
        response = self.client.post(
            reverse("course_toggle_lock", args=[self.course.pk])
        )
        self.course.refresh_from_db()
        self.assertFalse(self.course.locked)


class TestCourseCompleteAll(CourseViewTestBase):
    def test_marks_all_complete(self):
        response = self.client.post(
            reverse("course_complete_all", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        wh = WatchHistory.objects.get(course_node=self.video_node)
        self.assertTrue(wh.completed)

    def test_returns_course_content(self):
        response = self.client.post(
            reverse("course_complete_all", args=[self.course.pk])
        )
        self.assertContains(response, "course-content")


class TestCourseResetAll(CourseViewTestBase):
    def test_resets_all_progress(self):
        WatchHistory.objects.create(
            course_node=self.video_node,
            completed=True,
            duration_watched=300.0,
        )
        response = self.client.post(
            reverse("course_reset_all", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            WatchHistory.objects.filter(course_node=self.video_node).exists()
        )


class TestCourseProgressPartial(CourseViewTestBase):
    def test_returns_progress_card(self):
        response = self.client.get(
            reverse("course_progress_partial", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "course-progress")


class TestToggleComplete(CourseViewTestBase):
    def test_marks_file_complete(self):
        response = self.client.post(
            reverse("toggle_complete", args=[self.course.pk, self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        wh = WatchHistory.objects.get(course_node=self.video_node)
        self.assertTrue(wh.completed)

    def test_unmarks_completed_file(self):
        WatchHistory.objects.create(
            course_node=self.video_node,
            completed=True,
            duration_watched=300.0,
        )
        response = self.client.post(
            reverse("toggle_complete", args=[self.course.pk, self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            WatchHistory.objects.filter(
                course_node=self.video_node, completed=True
            ).exists()
        )


class TestToggleFileComplete(CourseViewTestBase):
    def test_returns_progress_panel(self):
        response = self.client.post(
            reverse("toggle_file_complete", args=[self.course.pk, self.video_node.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "file-progress-panel")


class TestTagList(TestCase):
    def setUp(self):
        self.client = Client()
        Tag.objects.all().delete()

    def test_get_shows_tags(self):
        Tag.objects.create(name="TestTag1", slug="testtag1", color="#3776ab")
        response = self.client.get(reverse("tag_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestTag1")

    def test_post_creates_tag(self):
        response = self.client.post(
            reverse("tag_list"), {"name": "NewTag", "color": "#092E20"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tag.objects.filter(name="NewTag").exists())


class TestTagEdit(TestCase):
    def setUp(self):
        self.client = Client()
        self.tag = Tag.objects.create(name="EditTag", slug="edittag", color="#3776ab")

    def test_get_shows_form(self):
        response = self.client.get(reverse("tag_edit", args=[self.tag.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EditTag")

    def test_post_updates_tag(self):
        response = self.client.post(
            reverse("tag_edit", args=[self.tag.pk]),
            {"name": "EditTag2", "color": "#ff0000"},
        )
        self.assertEqual(response.status_code, 302)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, "EditTag2")
        self.assertEqual(self.tag.color, "#ff0000")


class TestTagDelete(TestCase):
    def setUp(self):
        self.client = Client()
        self.tag = Tag.objects.create(name="Test", slug="test")

    def test_get_shows_confirmation(self):
        response = self.client.get(reverse("tag_delete", args=[self.tag.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete")

    def test_post_deletes_tag(self):
        response = self.client.post(reverse("tag_delete", args=[self.tag.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tag.objects.filter(pk=self.tag.pk).exists())


class TestTagCourses(TestCase):
    def setUp(self):
        self.client = Client()
        Tag.objects.all().delete()
        self.workspace = Workspace.objects.create(name="Test")
        self.tag = Tag.objects.create(name="CourseTag", slug="coursetag")
        self.course = Course.objects.create(
            workspace=self.workspace,
            title="Tagged Course",
            root_path="/tmp/tagged",
        )
        self.course.tags.add(self.tag)

    def test_shows_filtered_courses(self):
        response = self.client.get(reverse("tag_courses", args=[self.tag.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tagged Course")
