//imports


//classes


public class MinitesterTemplate {
    static String[] tests = {
        //tests
    };
    public static void main(String[] args) {
        int numPassed = 0;
        for(String className: tests)    {
            System.out.printf("%n======= %s =======%n", className);
            try {
                Runnable testCase = (Runnable) Class.forName(className).getDeclaredConstructor().newInstance();
                testCase.run();
                numPassed++;
            } catch (AssertionError e) {
                System.out.println(e);
            } catch (Exception e) {
                e.printStackTrace(System.out);
            }
        }
        System.out.printf("%n%n%d of %d tests passed.%n", numPassed, tests.length);
    }
}
