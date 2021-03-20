package _autograder;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.util.concurrent.*;

public class Executor {
    private static long getTimeout() {
        try {
            return Long.parseLong(System.getProperty("timeout"));
        } catch (Exception e) {
            return 3000;
        }
    }

    private static String escapeString(String s) {
        StringBuffer sb = new StringBuffer();
        final int len = s.length();
		for(int i = 0;i < len; i++){
			char ch = s.charAt(i);
			switch(ch){
			case '"':
				sb.append("\\\"");
				break;
			case '\\':
				sb.append("\\\\");
				break;
			case '\b':
				sb.append("\\b");
				break;
			case '\f':
				sb.append("\\f");
				break;
			case '\n':
				sb.append("\\n");
				break;
			case '\r':
				sb.append("\\r");
				break;
			case '\t':
				sb.append("\\t");
				break;
			case '/':
				sb.append("\\/");
				break;
			default:
                //Reference: http://www.unicode.org/versions/Unicode5.1.0/
				if((ch>='\u0000' && ch<='\u001F') || (ch>='\u007F' && ch<='\u009F') || (ch>='\u2000' && ch<='\u20FF')){
					String ss=Integer.toHexString(ch);
					sb.append("\\u");
					for(int k=0;k<4-ss.length();k++){
						sb.append('0');
					}
					sb.append(ss.toUpperCase());
				}
				else{
					sb.append(ch);
				}
			}
		}//for
        return sb.toString();
    }

    public static void main(String[] args) throws IOException {
        ByteArrayOutputStream newBaos = new ByteArrayOutputStream();
        PrintStream newPS = new PrintStream(newBaos);
        PrintStream oldPS = System.out;

        String className = System.getProperty("className");
        String testcaseID = System.getProperty("testcaseID");
        String isExternal = System.getProperty("isExternal");
        long timeout = getTimeout();
        boolean passed = false;
        String errorType = "";
        String errorMessage = "";

        try {
            ExecutorService service = Executors.newSingleThreadExecutor((Runnable r) -> {
                Thread t = new Thread(r);
                t.setDaemon(true);
                return t;
            });
            System.setOut(newPS);
            Runnable testCase = (Runnable) Class.forName(className).getDeclaredConstructor().newInstance();
            Future<?> future = service.submit(testCase);
            future.get(timeout, TimeUnit.MILLISECONDS);
            passed = true;
        } catch (Throwable exc) {
            Throwable error = exc instanceof ExecutionException ? exc.getCause() : exc;
            errorType = error.getClass().getCanonicalName();
            errorMessage = error.toString();
            if (error instanceof TimeoutException) {
                String msg = String.format("Timeout after %d milliseconds. You code may contain infinite loop.", timeout);
                newPS.println(msg);
            } else if (error instanceof AssertionError) {
                newPS.println(error.getMessage());
            } else {
                error.printStackTrace(newPS);
            }
        } finally {
            newPS.flush();
            String log = String.format("--------- Output ---------%n%s", newBaos.toString());
            String code = TestCode.data.get(className);
            if (code != null) {
                log = String.format("--------- Test Code ---------%n%s%n%n%s", code, log);
            }

            log = String.format("********* %s ********* %s%n%s%n%n%n",
                    testcaseID.replace("_@_", " : "),
                    passed ? "[PASSED]" : "[FAILED]", log);

            String line;
            if (isExternal == null) {
                line = String.format("{\"id\": \"%s\", \"passed\": %s, \"log\": \"%s\"}",
                        testcaseID, passed, escapeString(log));
            } else {
                line = String.format("{\"id\": \"%s\", \"passed\": %s, \"log\": \"%s\", " +
                                "\"timeout\": %d, " + "\"error_type\": \"%s\", \"error_message\": \"%s\"}",
                        testcaseID, passed, escapeString(log), timeout,
                        errorType, escapeString(errorMessage));
            }
            oldPS.println(line);
            oldPS.flush();
        }

    }
}
