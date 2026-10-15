import { formatDayMonth } from "../format";

// The y-axis top: an even number at least as big as the busiest week, so the middle line is a whole number.
function axisTop(weeks) {
  const busiest = Math.max(...weeks.map((week) => week.completions));
  return Math.max(2, Math.ceil(busiest / 2) * 2);
}

function weekLabel(week) {
  const completions = `${week.completions} ${week.completions === 1 ? "completion" : "completions"}`;
  return `Week of ${formatDayMonth(week.week_start)}: ${completions}${week.partial ? " so far" : ""}`;
}

// Course completions per week, oldest week first, as columns. Built from plain HTML boxes rather than SVG, so
// the labels keep their size on a phone. One series, so no legend: the heading says what is plotted. Hovering
// a column shows its number; the same numbers are in the table below the chart, for screen readers too.
export default function WeeklyCompletionsChart({ weeks }) {
  const top = axisTop(weeks);
  const ticks = [top, top / 2, 0];

  return (
    <figure className="space-y-3">
      {/* The drawing repeats the table, so screen readers skip it and read the table instead. */}
      <div aria-hidden="true">
        <div className="flex gap-2">
          {/* The y-axis numbers, level with the grid lines. */}
          <div className="relative h-48 w-6 text-right text-xs text-muted tabular-nums">
            {ticks.map((tick) => (
              <span key={tick} className="absolute right-0 translate-y-1/2" style={{ bottom: `${(tick / top) * 100}%` }}>
                {tick}
              </span>
            ))}
          </div>
          <div className="relative h-48 flex-1">
            {ticks.map((tick) => (
              <div
                key={tick}
                className="absolute inset-x-0 border-t border-line"
                style={{ bottom: `${(tick / top) * 100}%` }}
              />
            ))}
            {/* Eight equal columns. Each whole column is the hover target, not just its bar. */}
            <div className="absolute inset-0 grid grid-cols-8 gap-1">
              {weeks.map((week) => (
                <div key={week.week_start} title={weekLabel(week)} className="group flex items-end justify-center">
                  <div
                    className="w-full max-w-6 rounded-t bg-chart group-hover:opacity-80"
                    style={{ height: `${(week.completions / top) * 100}%` }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
        {/* The week labels, under their columns: the same 8-column grid, after the y-axis's width. */}
        <div className="ml-8 grid grid-cols-8 gap-1 text-center text-xs text-muted">
          {weeks.map((week) => (
            // The current week isn't over yet, so its label says "so far".
            <span key={week.week_start}>
              {formatDayMonth(week.week_start)}
              {week.partial && <span className="block">so far</span>}
            </span>
          ))}
        </div>
      </div>

      <figcaption className="text-sm text-muted">
        Courses completed each week over the last 8 weeks. Weeks start on Monday, in UTC; the last one isn't
        over yet.
      </figcaption>

      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-accent">Show as a table</summary>
        <table className="mt-2 text-left">
          <thead className="text-xs tracking-wider text-muted uppercase">
            <tr>
              <th scope="col" className="py-2 pr-6 font-medium">
                Week starting
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Completions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {weeks.map((week) => (
              <tr key={week.week_start}>
                <td className="py-2 pr-6">
                  {formatDayMonth(week.week_start)}
                  {week.partial && " (so far)"}
                </td>
                <td className="py-2 text-right tabular-nums">{week.completions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
