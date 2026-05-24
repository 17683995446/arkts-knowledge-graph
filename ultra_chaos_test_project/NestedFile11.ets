/**
 * 深度嵌套结构测试文件
 */

export class Outer11 {
    middle: Middle11 = new Middle11();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle11 {
    inner: Inner11 = new Inner11();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner11 {
    deeplyNested: DeeplyNested11 = new DeeplyNested11();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested11 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
