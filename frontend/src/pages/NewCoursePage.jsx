import { useNavigate } from "react-router";
import { createCourse } from "../api/courses";
import CourseForm from "../components/CourseForm";

// Every course starts as a draft. Only instructors may create one: anyone else who opens this address and
// submits gets the server's 403, which the form shows.
export default function NewCoursePage() {
  const navigate = useNavigate();

  async function handleCreate(values) {
    const course = await createCourse(values);
    navigate(`/courses/${course.id}`);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">New course</h1>
        <p className="text-muted">It starts as a draft. Add its lessons, then publish it from its page.</p>
      </div>
      <CourseForm
        submitLabel="Create course"
        busyLabel="Creating…"
        onSubmit={handleCreate}
        onCancel={() => navigate(-1)}
      />
    </div>
  );
}
