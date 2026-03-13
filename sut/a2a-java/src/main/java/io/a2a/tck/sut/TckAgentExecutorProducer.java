package io.a2a.tck.sut;

import java.util.List;
import java.util.Map;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

import io.a2a.server.agentexecution.AgentExecutor;
import io.a2a.server.agentexecution.RequestContext;
import io.a2a.server.tasks.AgentEmitter;
import io.a2a.spec.A2AError;
import io.a2a.spec.DataPart;
import io.a2a.spec.FileWithBytes;
import io.a2a.spec.FilePart;
import io.a2a.spec.TaskNotCancelableError;
import io.a2a.spec.TextPart;

/**
 * CDI producer for the TCK agent executor.
 *
 * <p>Generated from Gherkin scenarios — do not edit by hand.
 */
@ApplicationScoped
public class TckAgentExecutorProducer {

    @Produces
    public AgentExecutor agentExecutor() {
        return new AgentExecutor() {
            @Override
            public void execute(RequestContext context, AgentEmitter emitter) throws A2AError {
                String messageId = context.getMessage().messageId();

                if (messageId.startsWith("tck-send-001")) {
                    emitter.sendMessage(List.of(new TextPart("Hello from TCK")));
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-terminal-send-002")) {
                    emitter.sendMessage(List.of(new TextPart("Task completed")));
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-artifact-text")) {
                    emitter.addArtifact(List.of(new TextPart("Generated text content")), null, null, null);
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-artifact-file")) {
                    emitter.addArtifact(List.of(new FilePart(new FileWithBytes("text/plain", "output.txt", "dGNr"))), null, null, null);
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-artifact-data")) {
                    emitter.addArtifact(List.of(new DataPart("{\"key\": \"value\", \"count\": 42}")), null, null, null);
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-message-response")) {
                    emitter.sendMessage(List.of(new TextPart("Direct message response")));
                    return;
                }

                if (messageId.startsWith("tck-input-required")) {
                    emitter.requiresInput();
                    return;
                }

                if (messageId.startsWith("tck-reject-task")) {
                    throw new A2AError(-1, "rejected", null);
                }

                if (messageId.startsWith("tck-block-001")) {
                    emitter.sendMessage(List.of(new TextPart("Blocking response")));
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-block-002")) {
                    emitter.sendMessage(List.of(new TextPart("Non-blocking response")));
                    emitter.complete();
                    return;
                }

                if (messageId.startsWith("tck-task-helper")) {
                    emitter.sendMessage(List.of(new TextPart("Task helper response")));
                    emitter.complete();
                    return;
                }

                // Default: complete the task with an echo response
                emitter.sendMessage("Unhandled messageId prefix: " + messageId);
                emitter.complete();
            }

            @Override
            public void cancel(RequestContext context, AgentEmitter emitter) throws A2AError {
                emitter.cancel();
            }
        };
    }
}
