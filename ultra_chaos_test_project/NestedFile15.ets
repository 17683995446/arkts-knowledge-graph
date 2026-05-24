/**
 * 深度嵌套结构测试文件
 */

export class Outer15 {
    middle: Middle15 = new Middle15();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle15 {
    inner: Inner15 = new Inner15();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner15 {
    deeplyNested: DeeplyNested15 = new DeeplyNested15();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested15 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
