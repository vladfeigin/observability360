import { onFID, onLCP, onCLS, onINP } from 'web-vitals/attribution';
import { InstrumentationBase } from '@opentelemetry/instrumentation';
import { trace, context } from '@opentelemetry/api';
import { hrTime } from '@opentelemetry/core';

export class WebVitalsInstrumentation extends InstrumentationBase {
  onReport(metric, parentSpanContext) {
    console.log(metric)
    const now = hrTime();
    const webVitalsSpan = trace
      .getTracer('web-vitals-instrumentation')
      .startSpan(metric.name, { startTime: now }, parentSpanContext);

    webVitalsSpan.setAttributes({
      [`web_vital.name`]: metric.name,
      [`web_vital.id`]: metric.id,
      [`web_vital.navigationType`]: metric.navigationType,
      [`web_vital.delta`]: metric.delta,
      [`web_vital.rating`]: metric.rating,
      [`web_vital.value`]: metric.value,
      // can expand these into their own attributes!
      [`web_vital.entries`]: JSON.stringify(metric.entries),
      [`http.url`]: window.location.href,
      [`http.route`]: window.location.pathname,
    });

    switch (metric.name) {
      case 'LCP':
        webVitalsSpan.setAttributes({
          'web_vital.lcp.element': metric.attribution.element
        });
        break;

      case 'CLS':
        webVitalsSpan.setAttributes({
          'web_vital.cls.largestShiftTarget': metric.attribution.largestShiftTarget
        });
        break;
      case 'FID':
        webVitalsSpan.setAttributes({
          'web_vital.fid.eventTarget': metric.attribution.eventTarget
        });
        break;
      case 'INP':
        webVitalsSpan.setAttributes({
          'web_vital.inp.eventTarget': metric.attribution.eventTarget
        });
        break;
    
      default:
        break;
    }
    webVitalsSpan.end();
  }

  enable() {
    if (this.enabled) {
      return;
    }
    this.enabled = true;

    // create a parent span that will have all web vitals spans as children
    const parentSpan = trace.getTracer('web-vitals-instrumentation').startSpan('web-vitals');
    const ctx = trace.setSpan(context.active(), parentSpan);
    parentSpan.end();

    onFID((metric) => {
      this.onReport(metric, ctx);
    });
    onCLS((metric) => {
      this.onReport(metric, ctx);
    });
    onLCP((metric) => {
      this.onReport(metric, ctx);
    });
    onINP((metric) => {
      this.onReport(metric, ctx);
    });
  }
}