// tracing.js
import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { Resource }  from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { SeverityNumber } from '@opentelemetry/api-logs';
import { LoggerProvider, BatchLogRecordProcessor, SimpleLogRecordProcessor, ConsoleLogRecordExporter} from '@opentelemetry/sdk-logs';
import { WebVitalsInstrumentation } from './web-vitals-instrumentation';
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-http';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';


const logsCollectorOptions = {
  url: 'http://omerfdemo-otel-collector.swedencentral.azurecontainer.io:4318/v1/logs'
};

const tracesCollectorOptions = {
  url: 'http://omerfdemo-otel-collector.swedencentral.azurecontainer.io:4318/v1/traces'
};

const logExporter = new OTLPLogExporter(logsCollectorOptions);

console.log(process.env.OTEL_EXPORTER_OTLP_ENDPOINT)
const loggerProvider = new LoggerProvider();


loggerProvider.addLogRecordProcessor(new BatchLogRecordProcessor(logExporter));
loggerProvider.addLogRecordProcessor(new SimpleLogRecordProcessor(new ConsoleLogRecordExporter()));


const logger = loggerProvider.getLogger('default', '1.0.0');

logger.emit({
    severityNumber: SeverityNumber.INFO,
    severityText: 'info',
    body: 'User navigated to the application',
    attributes: { 'log.type': 'custom' },
});

const exporter = new OTLPTraceExporter(tracesCollectorOptions);

// The TracerProvider is the core library for creating traces
const provider = new WebTracerProvider({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'react-otel-experiment',
  }),
});

// The processor sorts through data as it comes in, before it is sent to the exporter
provider.addSpanProcessor(new BatchSpanProcessor(exporter));

// A context manager allows OTel to keep the context of function calls across async functions
// ensuring you don't have disconnected traces
provider.register({
  contextManager: new ZoneContextManager()
});

// Register instrumentations
// registerInstrumentations({
//   instrumentations: [
//     getWebAutoInstrumentations(),
//     new WebVitalsInstrumentation()
//   ],
// });