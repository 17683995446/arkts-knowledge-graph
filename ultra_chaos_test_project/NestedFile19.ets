/**
 * 深度嵌套结构测试文件
 */

export class Outer19 {
    middle: Middle19 = new Middle19();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle19 {
    inner: Inner19 = new Inner19();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner19 {
    deeplyNested: DeeplyNested19 = new DeeplyNested19();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested19 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
