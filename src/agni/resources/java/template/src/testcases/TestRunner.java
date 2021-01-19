import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.concurrent.*;
import java.util.stream.Collectors;

public class TestRunner {
    public static void main(String[] args) throws IOException {
        long defaultTimeout = 10000;
        Path testcasesPath = Paths.get("./src/testcases/exposed");
        // System.out.println(testcasesPath.toAbsolutePath());
        String pattern = ".*";
        int numPassed = 0;
        List<String> filepaths = Files.walk(testcasesPath).map(p -> testcasesPath.relativize(p).toString())
                .filter(p -> p.endsWith(".java") && p.matches(pattern)).sorted().collect(Collectors.toList());
        ExecutorService service = Executors.newCachedThreadPool((Runnable r) -> {
            Thread t = new Thread(r);
            t.setDaemon(true);
            return t;
        });
        for (String f : filepaths) {
            // System.out.println(p);
            String className = f.replace(".java", "").replace("/", ".");
            System.out.printf("%n======= %s =======%n", className);
            try {
                Runnable testCase = (Runnable) Class.forName(className).getDeclaredConstructor().newInstance();
                Future<?> future = service.submit(testCase);
                future.get(defaultTimeout, TimeUnit.MILLISECONDS);
                numPassed++;
            } catch (Throwable exc) {
                Throwable error = exc instanceof ExecutionException ? exc.getCause() : exc;
                if (error instanceof TimeoutException) {
                    String msg = String.format("Timeout after %d milliseconds. You code may contain infinite loop.", defaultTimeout);
                    System.out.println(msg);
                } else if (error instanceof AssertionError) {
                    System.out.println(error.toString());
                } else {
                    error.printStackTrace(System.out);
                }
            }
        }
        System.out.printf("%n%n%d of %d tests passed.%n", numPassed, filepaths.size());
    }
}